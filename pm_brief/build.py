import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from pm_brief.cache import cached_articles_for_sources, load_feed_cache, update_feed_cache, write_feed_cache
from pm_brief.config import load_config, load_sources, resolve_config_path
from pm_brief.dedupe import dedupe_articles
from pm_brief.fetch import fetch_articles
from pm_brief.health import filter_sources_by_health, load_source_health
from pm_brief.models import Article, Brief, LearningCard, ScoreBreakdown, ScoredArticle, Source
from pm_brief.scoring import ScoreWeights, extract_keywords, score_article


LATEST_REPORT_NAME = "today.md"

LEARNING_CARDS = [
    LearningCard(
        concept="RAG",
        explanation="RAG 是 Retrieval-Augmented Generation，先检索可信资料，再让大模型基于资料回答。",
        scenario="客服助手、经营诊断、政策问答都可以用 RAG 减少幻觉。",
        relation="商家成长产品可以用 RAG 把规则、工具教程和经营数据连接起来，给商家更可靠的建议。",
        english_expression="RAG grounds model answers in retrieved business context.",
    ),
    LearningCard(
        concept="Retail Media",
        explanation="零售媒体是平台把站内流量、用户意图和交易数据转化为广告与营销能力。",
        scenario="商家在搜索、推荐、详情页等场景投放，并用成交数据衡量效果。",
        relation="商家成长产品需要帮助商家理解投放回报、流量质量和自然增长之间的关系。",
        english_expression="Retail media turns marketplace traffic into measurable advertising inventory.",
    ),
    LearningCard(
        concept="Seller Lifecycle",
        explanation="商家生命周期描述商家从入驻、冷启动、成长、成熟到流失预警的阶段变化。",
        scenario="不同阶段的商家需要不同任务、工具、激励和经营诊断。",
        relation="京东 POP 商家成长可以围绕生命周期设计分层成长路径，而不是给所有商家同一套工具。",
        english_expression="Seller lifecycle design matches growth interventions to merchant maturity.",
    ),
    LearningCard(
        concept="Conversion Funnel",
        explanation="转化漏斗把用户从曝光、点击、加购到成交的过程拆成可诊断环节。",
        scenario="商家可以定位是流量不足、点击率低、详情页弱，还是价格和履约影响成交。",
        relation="商家成长产品应把指标解释成动作建议，帮助商家知道下一步该优化什么。",
        english_expression="A conversion funnel turns business outcomes into diagnosable steps.",
    ),
]

MUST_READ_THRESHOLD = 3.0
WATCH_THRESHOLD = 2.8
MARKETPLACE_THRESHOLD = 2.65


def generate_brief(
    config_path: Path,
    output_dir: Path,
    archive_path: Path,
    brief_date: date,
    candidate_articles: Iterable[Article] = (),
) -> Path:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{brief_date.isoformat()}.md"
    sources = load_sources(config)
    configured_source_count = len(sources)
    health_path = resolve_config_path(config_path, config.get("source_health_path", "data/source_health.json"))
    feed_cache_path = resolve_config_path(config_path, config.get("feed_cache_path", "data/feed_cache.json"))
    health = load_source_health(health_path)
    sources = filter_sources_by_health(sources, health, include_unstable=bool(config.get("include_unstable_sources", False)))
    skipped_source_count = configured_source_count - len(sources)
    articles = fetch_articles(
        sources,
        limit_per_source=int(config.get("limit_per_source", 8)),
        timeout=int(config.get("fetch_timeout_seconds", 6)),
        max_workers=int(config.get("max_fetch_workers", 8)),
    )
    failed_sources = [article.source.name for article in articles if article.title.startswith("[Fetch warning]")]
    live_articles = [article for article in articles if not article.title.startswith("[Fetch warning]")]
    feed_cache = load_feed_cache(feed_cache_path)
    if live_articles:
        feed_cache = update_feed_cache(
            feed_cache,
            live_articles,
            fetched_at=datetime.now(timezone.utc),
            retention_days=int(config.get("feed_cache_retention_days", 7)),
        )
        write_feed_cache(feed_cache_path, feed_cache)
    candidate_articles = list(candidate_articles)
    reference_time = datetime.combine(brief_date, datetime.max.time(), tzinfo=timezone.utc)
    fresh_articles = _filter_recent_real_articles(
        [*candidate_articles, *live_articles],
        days=int(config.get("lookback_days", 3)),
        reference_time=reference_time,
    )
    fallback_mode = ""
    scored: List[ScoredArticle] = []
    if not fresh_articles:
        cached_articles = _filter_recent_real_articles(
            [
                *candidate_articles,
                *cached_articles_for_sources(
                    feed_cache,
                    sources,
                    max_age_days=int(config.get("feed_cache_retention_days", 7)),
                    reference_time=reference_time,
                ),
            ],
            days=max(int(config.get("lookback_days", 3)), int(config.get("feed_cache_retention_days", 7))),
            reference_time=reference_time,
        )
        if cached_articles:
            fresh_articles = cached_articles
            fallback_mode = "feed_cache"
    if not fresh_articles:
        scored = _load_archive_fallback_scored(
            archive_path=archive_path,
            known_sources=sources,
            brief_date=brief_date,
            days=max(int(config.get("lookback_days", 3)), 7),
            limit=24,
        )
        if scored:
            fallback_mode = "archive"
    if not fresh_articles and not scored and (output_path.exists() or (output_dir / LATEST_REPORT_NAME).exists()):
        preserved_path = output_path if output_path.exists() else output_dir / LATEST_REPORT_NAME
        if output_path.exists():
            write_latest_copy(output_path, output_dir)
        write_status(
            output_dir,
            _run_status(
                brief_date=brief_date,
                output_path=output_path,
                source_count=len(sources),
                configured_source_count=configured_source_count,
                skipped_source_count=skipped_source_count,
                fetched_article_count=len(articles),
                candidate_article_count=len(candidate_articles),
                candidate_count=len(scored),
                scored_count=len(scored),
                must_read_count=0,
                ai_watch_count=0,
                marketplace_count=0,
                live_article_count=len(live_articles),
                failed_sources=failed_sources,
                preserved_existing=True,
                fallback_mode="preserved",
            ),
        )
        return preserved_path
    if not scored:
        scored = score_and_rank(dedupe_articles(fresh_articles), ScoreWeights.from_mapping(config.get("weights", {})))
    brief = build_brief(scored, brief_date)
    if fallback_mode and _fallback_is_too_weak(brief):
        preserved_path = _best_existing_report(output_dir, brief_date)
        if preserved_path is not None:
            if preserved_path.name != LATEST_REPORT_NAME:
                write_latest_copy(preserved_path, output_dir)
            write_status(
                output_dir,
                _run_status(
                    brief_date=brief_date,
                    output_path=preserved_path,
                    source_count=len(sources),
                    configured_source_count=configured_source_count,
                    skipped_source_count=skipped_source_count,
                    fetched_article_count=len(articles),
                    candidate_article_count=len(candidate_articles),
                    candidate_count=len(fresh_articles) if fresh_articles else len(scored),
                    scored_count=len(scored),
                    must_read_count=len(brief.must_reads),
                    ai_watch_count=len(brief.ai_product_watch),
                    marketplace_count=len(brief.marketplace_signals),
                    live_article_count=len(live_articles),
                    failed_sources=failed_sources,
                    preserved_existing=True,
                    fallback_mode="preserved",
                ),
            )
            return preserved_path

    from pm_brief.render import render_markdown

    output_path.write_text(render_markdown(brief), encoding="utf-8")
    write_latest_copy(output_path, output_dir)
    append_archive(archive_path, scored, brief_date)
    write_status(
        output_dir,
        _run_status(
            brief_date=brief_date,
            output_path=output_path,
            source_count=len(sources),
            configured_source_count=configured_source_count,
            skipped_source_count=skipped_source_count,
            fetched_article_count=len(articles),
            candidate_article_count=len(candidate_articles),
            candidate_count=len(fresh_articles) if fresh_articles else len(scored),
            scored_count=len(scored),
            must_read_count=len(brief.must_reads),
            ai_watch_count=len(brief.ai_product_watch),
            marketplace_count=len(brief.marketplace_signals),
            live_article_count=len(live_articles),
            failed_sources=failed_sources,
            preserved_existing=False,
            fallback_mode=fallback_mode,
        ),
    )
    return output_path


def write_status(output_dir: Path, status: dict) -> Path:
    status_path = output_dir / "status.md"
    failed_sources = status.get("failed_sources") or []
    failed_text = ", ".join(failed_sources) if failed_sources else "None"
    lines = [
        "# Daily PM Growth Brief Status",
        "",
        f"- Brief date: {status['brief_date']}",
        f"- Output path: {status['output_path']}",
        f"- Source count: {status['source_count']}",
        f"- Configured source count: {status.get('configured_source_count', status['source_count'])}",
        f"- Skipped unstable source count: {status.get('skipped_source_count', 0)}",
        f"- Fetched article count: {status['fetched_article_count']}",
        f"- Candidate article count: {status.get('candidate_article_count', 0)}",
        f"- Candidate count: {status['candidate_count']}",
        f"- Scored count: {status['scored_count']}",
        f"- Must Read count: {status['must_read_count']}",
        f"- AI Product Watch count: {status['ai_watch_count']}",
        f"- Marketplace count: {status['marketplace_count']}",
        f"- Live article count: {status.get('live_article_count', 0)}",
        f"- Preserved existing report: {status.get('preserved_existing', False)}",
        f"- Fallback mode: {status.get('fallback_mode', 'none')}",
        f"- Failed sources: {failed_text}",
        "",
    ]
    status_path.write_text("\n".join(lines), encoding="utf-8")
    return status_path


def _run_status(
    brief_date: date,
    output_path: Path,
    source_count: int,
    configured_source_count: int,
    skipped_source_count: int,
    fetched_article_count: int,
    candidate_article_count: int,
    candidate_count: int,
    scored_count: int,
    must_read_count: int,
    ai_watch_count: int,
    marketplace_count: int,
    live_article_count: int,
    failed_sources: List[str],
    preserved_existing: bool,
    fallback_mode: str = "",
) -> dict:
    return {
        "brief_date": brief_date.isoformat(),
        "output_path": str(output_path),
        "source_count": source_count,
        "configured_source_count": configured_source_count,
        "skipped_source_count": skipped_source_count,
        "fetched_article_count": fetched_article_count,
        "candidate_article_count": candidate_article_count,
        "candidate_count": candidate_count,
        "scored_count": scored_count,
        "must_read_count": must_read_count,
        "ai_watch_count": ai_watch_count,
        "marketplace_count": marketplace_count,
        "live_article_count": live_article_count,
        "failed_sources": failed_sources,
        "preserved_existing": preserved_existing,
        "fallback_mode": fallback_mode or "none",
    }


def write_latest_copy(daily_report_path: Path, output_dir: Path) -> Path:
    latest_path = output_dir / LATEST_REPORT_NAME
    latest_path.write_text(daily_report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return latest_path


def score_and_rank(articles: Iterable[Article], weights: ScoreWeights = ScoreWeights.default()) -> List[ScoredArticle]:
    scored = [
        ScoredArticle(article=article, score=score_article(article, weights), keywords=extract_keywords(article))
        for article in articles
        if not article.title.startswith("[Fetch warning]")
    ]
    return sorted(scored, key=lambda item: item.score.total, reverse=True)


def build_brief(scored: List[ScoredArticle], brief_date: date) -> Brief:
    must_reads = [item for item in scored if item.score.total >= MUST_READ_THRESHOLD][:3]
    ai_product_watch = _pick_by_category(scored, {"AI Frontier", "Product & Startup Signals"}, 3, WATCH_THRESHOLD)
    marketplace_signals = _pick_by_category(scored, {"E-commerce & Marketplace", "China Tech & Retail"}, 3, MARKETPLACE_THRESHOLD)
    cited = _unique_scored([*must_reads, *ai_product_watch, *marketplace_signals])
    return Brief(
        brief_date=brief_date,
        one_line_signal=_one_line_signal(cited),
        must_reads=must_reads,
        ai_product_watch=ai_product_watch,
        marketplace_signals=marketplace_signals,
        thinking_question=_thinking_question(cited),
        thinking_hints=[
            "先区分商家真正缺的是信息、判断，还是可执行动作。",
            "把 AI 能力放进经营链路时，要考虑不同成熟度商家的理解成本。",
            "好的商家工具不只展示指标，还要解释变化原因和下一步优先级。",
        ],
        learning_card=LEARNING_CARDS[brief_date.toordinal() % len(LEARNING_CARDS)],
        cited_articles=cited,
        tags=_tags(cited),
    )


def append_archive(path: Path, scored: Iterable[ScoredArticle], brief_date: date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for item in scored:
            payload = {
                "date": brief_date.isoformat(),
                "title": item.article.title,
                "url": item.article.url,
                "source": item.article.source.name,
                "category": item.article.source.category,
                "score": item.score.total,
                "published_at": item.article.published_at.isoformat() if item.article.published_at else None,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _load_archive_fallback_scored(
    archive_path: Path,
    known_sources: Iterable[Source],
    brief_date: date,
    days: int,
    limit: int,
) -> List[ScoredArticle]:
    if not archive_path.exists():
        return []

    source_map = {source.name: source for source in known_sources}
    cutoff = datetime.combine(brief_date, datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=days)
    entries: List[ScoredArticle] = []
    seen_urls = set()

    lines = archive_path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        payload = json.loads(line)
        published_at = _parse_archive_datetime(payload.get("published_at"))
        if published_at and published_at < cutoff:
            continue
        url = payload.get("url")
        title = payload.get("title")
        if not url or not title or url in seen_urls:
            continue
        source = source_map.get(payload.get("source")) or Source(
            name=payload.get("source", "Archive"),
            url=url,
            category=payload.get("category", "Product & Startup Signals"),
            quality=4,
            language="zh" if payload.get("category") == "China Tech & Retail" else "en",
        )
        article = Article(
            title=title,
            url=url,
            source=source,
            published_at=published_at,
            summary="",
        )
        total = float(payload.get("score", 3.0))
        entries.append(
            ScoredArticle(
                article=article,
                score=ScoreBreakdown(
                    impact=3,
                    novelty=3,
                    source_quality=source.quality,
                    pm_relevance=3,
                    actionability=3,
                    total=round(total, 2),
                ),
                keywords=extract_keywords(article),
            )
        )
        seen_urls.add(url)
        if len(entries) >= limit:
            break
    return list(reversed(entries))


def _parse_archive_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _fallback_is_too_weak(brief: Brief) -> bool:
    return len(brief.must_reads) == 0 and len(brief.ai_product_watch) == 0


def _best_existing_report(output_dir: Path, brief_date: date) -> Optional[Path]:
    dated_reports = sorted(output_dir.glob("*.md"), reverse=True)
    for path in dated_reports:
        if path.name in {"status.md", LATEST_REPORT_NAME}:
            continue
        try:
            report_date = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if report_date < brief_date:
            return path
    latest_path = output_dir / LATEST_REPORT_NAME
    if latest_path.exists():
        return latest_path
    return None


def _filter_recent_real_articles(articles: Iterable[Article], days: int, reference_time: Optional[datetime] = None) -> List[Article]:
    cutoff = (reference_time or datetime.now(timezone.utc)) - timedelta(days=days)
    filtered = []
    for article in articles:
        if article.title.startswith("[Fetch warning]"):
            continue
        if article.published_at is None or article.published_at >= cutoff:
            filtered.append(article)
    return filtered


def _pick_by_category(scored: List[ScoredArticle], categories: set, limit: int, threshold: float) -> List[ScoredArticle]:
    return [item for item in scored if item.article.source.category in categories and item.score.total >= threshold][:limit]


def _unique_scored(items: Iterable[ScoredArticle]) -> List[ScoredArticle]:
    seen = set()
    result = []
    for item in items:
        if item.article.url not in seen:
            seen.add(item.article.url)
            result.append(item)
    return result


def _one_line_signal(items: List[ScoredArticle]) -> str:
    if any("AI Agent" in item.keywords or "AI Workflow" in item.keywords for item in items):
        return "AI 正在从“回答问题”走向“执行经营流程”。"
    if any("Retail Media" in item.keywords for item in items):
        return "零售媒体和商家工具正在更深地绑定增长动作。"
    if any("Seller Tools" in item.keywords for item in items):
        return "平台竞争正在转向谁能更好地提升商家经营效率。"
    return "今天值得关注的是：新工具如何把复杂经营问题变成可执行动作。"


def _thinking_question(items: List[ScoredArticle]) -> str:
    if any("AI Analytics" in item.keywords for item in items):
        return "如果为 POP 商家设计 AI 数据分析助手，它应该优先解释指标异常，还是直接推荐经营动作？"
    if any("Retail Media" in item.keywords for item in items):
        return "如果商家同时面对自然流量和广告投放，平台应如何帮助他们判断增长来自哪里？"
    return "如果要为 POP 商家设计一个 AI 经营助手，第一阶段应优先解决“看不懂数据”还是“不会做动作”？"


def _tags(items: List[ScoredArticle]) -> List[str]:
    mapping = {
        "AI Agent": "#AI-Agent",
        "AI Workflow": "#AI-Workflow",
        "AI Analytics": "#AI-Analytics",
        "Retail Media": "#Retail-Media",
        "Seller Tools": "#Seller-Growth",
        "Marketplace": "#Marketplace",
        "China Tech": "#China-Tech",
    }
    tags = []
    for item in items:
        for keyword in item.keywords:
            tag = mapping.get(keyword)
            if tag and tag not in tags:
                tags.append(tag)
    if "#Seller-Growth" not in tags:
        tags.append("#Seller-Growth")
    if "#Product-Strategy" not in tags:
        tags.append("#Product-Strategy")
    return tags[:6]

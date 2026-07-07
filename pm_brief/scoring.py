import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

from pm_brief.models import Article, ScoreBreakdown


@dataclass(frozen=True)
class ScoreWeights:
    impact: float
    novelty: float
    source_quality: float
    pm_relevance: float
    actionability: float

    @classmethod
    def default(cls) -> "ScoreWeights":
        return cls(
            impact=0.30,
            novelty=0.25,
            source_quality=0.20,
            pm_relevance=0.15,
            actionability=0.10,
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, float]) -> "ScoreWeights":
        default = cls.default()
        return cls(
            impact=float(values.get("impact", default.impact)),
            novelty=float(values.get("novelty", default.novelty)),
            source_quality=float(values.get("source_quality", default.source_quality)),
            pm_relevance=float(values.get("pm_relevance", default.pm_relevance)),
            actionability=float(values.get("actionability", default.actionability)),
        )


KEYWORD_GROUPS: Dict[str, List[str]] = {
    "impact": [
        "launch",
        "released",
        "announces",
        "platform",
        "marketplace",
        "ads",
        "advertising",
        "retail media",
        "seller",
        "merchant",
        "enterprise",
        "partnership",
        "regulation",
        "price change",
        "opens",
        "global",
        "growth",
        "增长",
        "平台",
        "商家",
        "广告",
        "零售",
        "电商",
    ],
    "novelty": [
        "ai",
        "agent",
        "agents",
        "copilot",
        "browser",
        "search",
        "multimodal",
        "workflow",
        "automation",
        "rag",
        "analytics",
        "model",
        "reasoning",
        "assistant",
        "new",
        "frontier",
        "智能体",
        "大模型",
        "自动化",
        "多模态",
    ],
    "pm_relevance": [
        "seller",
        "merchant",
        "marketplace",
        "e-commerce",
        "ecommerce",
        "retail",
        "ads",
        "advertising",
        "conversion",
        "funnel",
        "analytics",
        "dashboard",
        "enterprise",
        "business",
        "workflow",
        "automation",
        "onboarding",
        "customer service",
        "supply chain",
        "fulfillment",
        "growth",
        "商家",
        "电商",
        "经营",
        "转化",
        "流量",
        "投放",
        "客服",
        "履约",
    ],
    "actionability": [
        "tool",
        "dashboard",
        "workflow",
        "automation",
        "playbook",
        "guide",
        "case study",
        "best practice",
        "template",
        "api",
        "integrations",
        "诊断",
        "工具",
        "方法",
        "实践",
        "数据",
    ],
}


HIGH_SIGNAL_KEYWORDS = {
    "AI Agent": ["agent", "agents", "智能体"],
    "AI Copilot": ["copilot", "assistant", "助手"],
    "AI Workflow": ["workflow", "automation", "自动化"],
    "AI Analytics": ["analytics", "data analysis", "dashboard", "数据分析"],
    "Retail Media": ["retail media", "ads", "advertising", "广告"],
    "Seller Tools": ["seller", "merchant", "商家"],
    "Marketplace": ["marketplace", "平台", "电商"],
    "Conversion Funnel": ["conversion", "funnel", "转化"],
    "RAG": ["rag", "retrieval"],
    "Multimodal": ["multimodal", "多模态"],
}


def score_article(article: Article, weights: ScoreWeights) -> ScoreBreakdown:
    text = _article_text(article)
    impact = _dimension_score(text, KEYWORD_GROUPS["impact"])
    novelty = _dimension_score(text, KEYWORD_GROUPS["novelty"])
    source_quality = _clamp(article.source.quality)
    pm_relevance = _dimension_score(text, KEYWORD_GROUPS["pm_relevance"])
    actionability = _dimension_score(text, KEYWORD_GROUPS["actionability"])

    if article.source.category in {"E-commerce & Marketplace", "China Tech & Retail"}:
        pm_relevance = min(5, pm_relevance + 1)
    if article.source.category == "AI Frontier":
        novelty = min(5, novelty + 1)
        if any(term in text for term in ["workflow", "analytics", "enterprise", "business", "automation"]):
            pm_relevance = min(5, pm_relevance + 1)
    if re.search(r"\b(stock|shares|earnings|财报|股价)\b", text) and not re.search(
        r"\b(strategy|launch|product|platform|ads|seller|merchant|战略|产品|平台|商家)\b",
        text,
    ):
        impact = max(1, impact - 2)
        actionability = max(1, actionability - 1)

    total = (
        impact * weights.impact
        + novelty * weights.novelty
        + source_quality * weights.source_quality
        + pm_relevance * weights.pm_relevance
        + actionability * weights.actionability
    )
    return ScoreBreakdown(
        impact=impact,
        novelty=novelty,
        source_quality=source_quality,
        pm_relevance=pm_relevance,
        actionability=actionability,
        total=round(total, 2),
    )


def extract_keywords(article: Article, limit: int = 5) -> List[str]:
    text = _article_text(article)
    found: List[str] = []
    for label, variants in HIGH_SIGNAL_KEYWORDS.items():
        if any(variant.lower() in text for variant in variants):
            found.append(label)
    if article.source.category == "Product & Startup Signals":
        found.append("Product Signal")
    if article.source.category == "China Tech & Retail":
        found.append("China Tech")
    return _unique(found)[:limit]


def _dimension_score(text: str, keywords: Iterable[str]) -> int:
    hits = sum(1 for keyword in keywords if keyword.lower() in text)
    if hits >= 8:
        return 5
    if hits >= 5:
        return 4
    if hits >= 3:
        return 3
    if hits >= 1:
        return 2
    return 1


def _article_text(article: Article) -> str:
    return f"{article.title} {article.summary} {article.source.name} {article.source.category}".lower()


def _clamp(value: int) -> int:
    return max(1, min(5, value))


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

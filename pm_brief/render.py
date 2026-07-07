from datetime import timezone
from typing import List

from pm_brief.models import Brief, ScoredArticle


KEYWORD_EXPLANATIONS = {
    "AI Agent": "能自主规划并执行任务的 AI 系统",
    "AI Copilot": "嵌入工作流的智能助手",
    "AI Workflow": "用 AI 串联和自动化多步骤任务",
    "AI Analytics": "用 AI 辅助数据分析和洞察生成",
    "Retail Media": "平台基于交易与流量数据提供的广告能力",
    "Seller Tools": "帮助商家经营、投放和履约的平台工具",
    "Marketplace": "连接商家、用户和服务商的平台市场",
    "Conversion Funnel": "从曝光到成交的转化路径",
    "RAG": "检索增强生成，让模型基于资料回答",
    "Multimodal": "同时处理文本、图片、音频或视频的能力",
    "Product Signal": "能提示新需求或新交互方式的产品信号",
    "China Tech": "中国科技与平台经济动态",
}


def render_markdown(brief: Brief) -> str:
    parts = [
        f"# Daily PM Growth Brief — {brief.brief_date.isoformat()}",
        "",
        "## 0. Today's One-Line Signal",
        "",
        brief.one_line_signal,
        "",
        "## 1. Must Read — 今天最重要的 3 条",
        "",
        _render_must_reads(brief.must_reads),
        "",
        "## 2. AI Product Watch — AI 产品观察",
        "",
        _render_ai_watch(brief.ai_product_watch),
        "",
        "## 3. Marketplace & Seller Growth — 商家成长相关信号",
        "",
        _render_marketplace(brief.marketplace_signals),
        "",
        "## 4. PM Thinking — 今天的产品经理思考题",
        "",
        brief.thinking_question,
        "",
        "思考提示：",
        *[f"- {hint}" for hint in brief.thinking_hints],
        "",
        "## 5. 5-Minute Learning Card — 今日学习卡片",
        "",
        f"**今日概念：** {brief.learning_card.concept}",
        "",
        f"**通俗解释：** {brief.learning_card.explanation}",
        "",
        f"**典型场景：** {brief.learning_card.scenario}",
        "",
        f"**和商家成长产品的关系：** {brief.learning_card.relation}",
        "",
        f"**英文表达：** {brief.learning_card.english_expression}",
        "",
        "## 6. 原文阅读清单",
        "",
        "| 标题 | 来源 | 发布时间 | 推荐阅读理由 | 链接 |",
        "| --- | --- | --- | --- | --- |",
        *[_reading_row(item) for item in brief.cited_articles],
        "",
        "## 7. 今日归档标签",
        "",
        " ".join(brief.tags),
        "",
    ]
    return "\n".join(parts)


def _render_must_reads(items: List[ScoredArticle]) -> str:
    if not items:
        return "今天没有筛出足够高质量的 Must Read。宁可少写，也不强行凑数。"
    blocks = []
    for index, item in enumerate(items, 1):
        article = item.article
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {article.title}",
                    "",
                    f"**发生了什么：** {_summary(article.summary, article.title)}",
                    "",
                    f"**为什么重要：** {_why_important(item)}",
                    "",
                    f"**对我的启发：** {_pm_takeaway(item)}",
                    "",
                    f"**可以积累的关键词：** {_keyword_text(item)}",
                    "",
                    f"**原文链接：** [{article.url}]({article.url})",
                    "",
                    f"**来源 / 发布时间：** {article.source.name} / {_date_text(item)}",
                    "",
                    f"**推荐阅读优先级：** {_priority(item)}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _render_ai_watch(items: List[ScoredArticle]) -> str:
    if not items:
        return "今天没有筛出足够明确的 AI 产品动态。"
    blocks = []
    for item in items:
        article = item.article
        blocks.append(
            "\n".join(
                [
                    f"### {article.source.name} / {article.title}",
                    "",
                    f"**新能力是什么：** {_summary(article.summary, article.title)}",
                    "",
                    f"**它解决了什么用户问题：** 帮用户把复杂信息处理、任务执行或数据判断变得更自动、更低门槛。",
                    "",
                    f"**交互或产品设计上值得学习：** 关注它是否把 AI 放进具体工作流，而不是停留在聊天入口。",
                    "",
                    f"**迁移到商家成长的机会：** 可思考是否能变成商家经营诊断、投放建议、客服辅助或自动化任务编排。",
                    "",
                    f"**原文链接：** [{article.url}]({article.url})",
                ]
            )
        )
    return "\n\n".join(blocks)


def _render_marketplace(items: List[ScoredArticle]) -> str:
    if not items:
        return "今天没有筛出足够明确的商家成长信号。"
    blocks = []
    for item in items:
        article = item.article
        blocks.append(
            "\n".join(
                [
                    f"### {article.title}",
                    "",
                    f"**事件概要：** {_summary(article.summary, article.title)}",
                    "",
                    "**影响的对象：** 商家 / 平台 / 服务商",
                    "",
                    f"**可能影响的经营环节：** {_growth_stage(item)}",
                    "",
                    f"**对京东 POP 商家成长的可借鉴点：** {_pm_takeaway(item)}",
                    "",
                    f"**原文链接：** [{article.url}]({article.url})",
                ]
            )
        )
    return "\n\n".join(blocks)


def _summary(summary: str, fallback: str) -> str:
    text = summary or fallback
    return text[:220] + ("..." if len(text) > 220 else "")


def _why_important(item: ScoredArticle) -> str:
    category = item.article.source.category
    if category == "AI Frontier":
        return "它可能改变用户获取信息、分析数据和执行任务的方式，进而影响平台工具的默认交互。"
    if category == "E-commerce & Marketplace":
        return "它直接关联商家经营效率、平台规则、流量分配或广告变现，是商家成长产品必须跟踪的外部变量。"
    if category == "China Tech & Retail":
        return "国内平台和云厂商的动作更接近你的业务语境，值得观察其产品化速度和落地方式。"
    return "它提供了新产品、新模式或新增长路径的信号，适合作为产品经理的案例库。"


def _pm_takeaway(item: ScoredArticle) -> str:
    if "Retail Media" in item.keywords:
        return "不要只把广告当投放入口，要把它和经营诊断、商品优化、转化漏斗放在一起设计。"
    if "AI Agent" in item.keywords or "AI Workflow" in item.keywords:
        return "商家工作台可以从“工具集合”升级为“任务型经营助手”，让系统主动拆解目标和下一步动作。"
    if "AI Analytics" in item.keywords:
        return "数据产品的价值不止在看板，而在解释异常、判断优先级，并让商家知道应该先做什么。"
    return "从商家成长视角看，重点不是新闻本身，而是它能否降低商家的理解成本、决策成本或执行成本。"


def _keyword_text(item: ScoredArticle) -> str:
    keywords = item.keywords or ["Marketplace", "Seller Tools", "Product Signal"]
    return "；".join(f"{keyword}：{KEYWORD_EXPLANATIONS.get(keyword, '值得持续积累的产品关键词')}" for keyword in keywords[:5])


def _growth_stage(item: ScoredArticle) -> str:
    text = f"{item.article.title} {item.article.summary}".lower()
    stages = []
    if any(word in text for word in ["onboarding", "入驻"]):
        stages.append("入驻")
    if any(word in text for word in ["ads", "advertising", "retail media", "traffic", "广告", "流量"]):
        stages.append("流量/广告")
    if any(word in text for word in ["conversion", "checkout", "转化"]):
        stages.append("转化")
    if any(word in text for word in ["fulfillment", "supply chain", "delivery", "履约", "供应链"]):
        stages.append("履约")
    if any(word in text for word in ["analytics", "dashboard", "data", "数据"]):
        stages.append("数据分析")
    if not stages:
        stages = ["选品", "流量", "转化", "数据分析"]
    return "、".join(stages)


def _reading_row(item: ScoredArticle) -> str:
    article = item.article
    return (
        f"| {article.title} | {article.source.name} | {_date_text(item)} | "
        f"{_priority(item)}，评分 {item.score.total} | [阅读]({article.url}) |"
    )


def _date_text(item: ScoredArticle) -> str:
    value = item.article.published_at
    if value is None:
        return "发布时间未明确"
    return value.astimezone(timezone.utc).date().isoformat()


def _priority(item: ScoredArticle) -> str:
    if item.score.total >= 4.2:
        return "High"
    if item.score.total >= 3.0:
        return "Medium"
    return "Low"

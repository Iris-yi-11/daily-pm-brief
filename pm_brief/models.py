from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    category: str
    quality: int
    language: str
    tier: int = 2
    failure_policy: str = "skip_when_unstable"


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: Source
    published_at: Optional[datetime]
    summary: str = ""


@dataclass(frozen=True)
class ScoreBreakdown:
    impact: int
    novelty: int
    source_quality: int
    pm_relevance: int
    actionability: int
    total: float


@dataclass(frozen=True)
class ScoredArticle:
    article: Article
    score: ScoreBreakdown
    keywords: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class LearningCard:
    concept: str
    explanation: str
    scenario: str
    relation: str
    english_expression: str


@dataclass(frozen=True)
class Brief:
    brief_date: date
    one_line_signal: str
    must_reads: List[ScoredArticle]
    ai_product_watch: List[ScoredArticle]
    marketplace_signals: List[ScoredArticle]
    thinking_question: str
    thinking_hints: List[str]
    learning_card: LearningCard
    cited_articles: List[ScoredArticle]
    tags: List[str]

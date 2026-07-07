# Web Candidate JSON Schema

When local RSS fetches fail or produce too few candidates, create a JSON file at:

```text
data/candidates/YYYY-MM-DD.json
```

The file must be a JSON array. Each item must include enough source metadata for traceability:

```json
[
  {
    "title": "Article title",
    "url": "https://source.example/article",
    "source": "Source name",
    "source_url": "https://source.example",
    "category": "AI Frontier",
    "quality": 5,
    "language": "en",
    "published_at": "2026-07-03T01:00:00+00:00",
    "summary": "Two or three factual sentences describing what happened and why it matters."
  }
]
```

Valid categories:

- `AI Frontier`
- `AI Product Video`
- `Product & Startup Signals`
- `E-commerce & Marketplace`
- `China Tech & Retail`

Minimum daily target:

- 18-30 candidate items.
- At least 8 AI Frontier or AI product items.
- At least 5 marketplace, retail media, seller tool, advertising, or ecommerce items.
- At least 3 China tech or China retail items when credible sources are available.

Do not include unsourced claims, social reposts without original links, or pure stock-price items.

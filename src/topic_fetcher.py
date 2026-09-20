"""
Pulls currently "hot" AI stories to turn into a LinkedIn post.

Source: Hacker News (via the free, keyless Algolia HN Search API), filtered
to AI-related keywords and sorted by points. Swap this out or add more
sources (arXiv, a company blog's RSS feed, etc.) without touching anything
else in the app — it just needs to return a list of Topic objects.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

import requests

AI_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "large language model", "gpt",
    "claude", "gemini", "openai", "anthropic", "machine learning",
    "neural network", "deep learning", "agent", "chatbot", "genai",
]

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


@dataclass
class Topic:
    title: str
    url: str
    points: int
    source: str = "Hacker News"


def _is_ai_related(title: str) -> bool:
    t = title.lower()
    return any(re.search(rf'\b{re.escape(keyword)}\b', t) for keyword in AI_KEYWORDS)


def fetch_hot_ai_topics(lookback_hours: int = 24, limit: int = 5) -> List[Topic]:
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{int(since.timestamp())}",
        "hitsPerPage": 100,
    }
    resp = requests.get(HN_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    candidates = [
        Topic(
            title=hit.get("title") or "",
            url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            points=hit.get("points") or 0,
        )
        for hit in hits
        if hit.get("title") and _is_ai_related(hit["title"])
    ]
    candidates.sort(key=lambda t: t.points, reverse=True)
    return candidates[:limit]


if __name__ == "__main__":
    for topic in fetch_hot_ai_topics():
        print(f"[{topic.points} pts] {topic.title} -> {topic.url}")

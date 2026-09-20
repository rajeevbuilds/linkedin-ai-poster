"""
Pulls currently "hot" AI stories to turn into a LinkedIn post.

Sources: Hacker News (via the free, keyless Algolia HN Search API), plus
optional GNews and NewsAPI searches, all filtered to AI-related keywords.
Swap this out or add more sources (arXiv, a company blog's RSS feed, etc.)
without touching anything else in the app — each fetcher just needs to
return a list of Topic objects.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

import requests

from src import config

AI_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "large language model", "gpt",
    "claude", "gemini", "openai", "anthropic", "machine learning",
    "neural network", "deep learning", "agent", "chatbot", "genai",
]

# Political/policy stories often mention "AI" in passing (regulation,
# funding, government adoption) without being technical AI content. This
# list may need occasional tuning as new political/AI-policy terms emerge.
EXCLUDE_KEYWORDS = [
    "president", "senate", "congress", "election", "czar", "regulation",
    "lawsuit", "administration", "white house", "policy", "legislation",
    "government shutdown", "impeach",
]

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"
NEWSAPI_TOP_HEADLINES_URL = "https://newsapi.org/v2/top-headlines"

GNEWS_QUERY = "artificial intelligence"


@dataclass
class Topic:
    title: str
    url: str
    points: int
    source: str = "Hacker News"


def _is_ai_related(title: str) -> bool:
    t = title.lower()
    return any(re.search(rf'\b{re.escape(keyword)}\b', t) for keyword in AI_KEYWORDS)


def _is_political(title: str) -> bool:
    t = title.lower()
    return any(re.search(rf'\b{re.escape(keyword)}\b', t) for keyword in EXCLUDE_KEYWORDS)


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


def fetch_gnews_topics(lookback_hours: int = 24, limit: int = 5) -> List[Topic]:
    """Best-effort. Returns [] if GNEWS_API_KEY isn't set or the request fails."""
    if not config.GNEWS_API_KEY:
        return []

    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    params = {
        "q": GNEWS_QUERY,
        "lang": "en",
        "from": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sortby": "publishedAt",
        "max": 10,  # free-tier cap
        "category": "technology",
        "apikey": config.GNEWS_API_KEY,
    }
    try:
        resp = requests.get(GNEWS_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception as exc:
        print(f"[topic_fetcher] GNews fetch failed ({exc}); skipping this source.")
        return []

    # GNews doesn't expose an engagement/vote count, so we assign a
    # descending synthetic rank (by result order) purely to sort candidates
    # from this source relative to each other. It is not a real popularity
    # signal like Hacker News points, and Hacker News stays the trusted
    # baseline for that reason.
    candidates = [
        Topic(title=a["title"], url=a["url"], points=max(1, 100 - i), source="GNews")
        for i, a in enumerate(articles)
        if a.get("title") and a.get("url") and _is_ai_related(a["title"])
    ]
    return candidates[:limit]


def fetch_newsapi_topics(lookback_hours: int = 24, limit: int = 5) -> List[Topic]:
    """Best-effort. Returns [] if NEWSAPI_API_KEY isn't set or the request fails.

    Uses /v2/top-headlines (category=technology&country=us) rather than
    /v2/everything, so results are restricted to NewsAPI's own technology
    category instead of a broad keyword search. Note: top-headlines doesn't
    support date-range filtering, so lookback_hours isn't applied here.
    """
    if not config.NEWSAPI_API_KEY:
        return []

    params = {
        "category": "technology",
        "country": "us",
        "pageSize": 20,
        "apiKey": config.NEWSAPI_API_KEY,
    }
    try:
        resp = requests.get(NEWSAPI_TOP_HEADLINES_URL, params=params, timeout=15)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception as exc:
        print(f"[topic_fetcher] NewsAPI fetch failed ({exc}); skipping this source.")
        return []

    # Same caveat as GNews above: synthetic rank, not a real engagement metric.
    candidates = [
        Topic(title=a["title"], url=a["url"], points=max(1, 100 - i), source="NewsAPI")
        for i, a in enumerate(articles)
        if a.get("title") and a.get("url") and _is_ai_related(a["title"])
    ]
    return candidates[:limit]


def _filter_political(topics: List[Topic]) -> List[Topic]:
    kept = []
    for topic in topics:
        if _is_political(topic.title):
            print(f"[topic_fetcher] Skipped (political/policy content): {topic.title}")
        else:
            kept.append(topic)
    return kept


def fetch_all_topics(lookback_hours: int = 24, limit: int = 5) -> List[Topic]:
    """
    Health-check / fallback order:
      1. Hacker News  — always tried, always trusted (real upvote counts).
      2. GNews        — optional, best-effort; skipped if no API key or on failure.
      3. NewsAPI      — optional, best-effort; skipped if no API key or on failure.
      4. If steps 1-3 combined return nothing usable, retry Hacker News alone
         with a doubled lookback window as a last resort.
      5. If even that returns nothing, return an empty list (main.py already
         handles this case with "No fresh AI topics found").
    """
    hn_topics = fetch_hot_ai_topics(lookback_hours=lookback_hours, limit=limit)
    gnews_topics = fetch_gnews_topics(lookback_hours=lookback_hours, limit=limit)
    newsapi_topics = fetch_newsapi_topics(lookback_hours=lookback_hours, limit=limit)

    combined: List[Topic] = []
    seen_urls = set()
    for topic in hn_topics + gnews_topics + newsapi_topics:
        if topic.url not in seen_urls:
            seen_urls.add(topic.url)
            combined.append(topic)

    combined = _filter_political(combined)

    if not combined:
        print(
            "[topic_fetcher] GNews/NewsAPI returned nothing usable — "
            "falling back to Hacker News only."
        )
        fallback = fetch_hot_ai_topics(lookback_hours=lookback_hours * 2, limit=limit)
        return _filter_political(fallback)

    combined.sort(key=lambda t: t.points, reverse=True)
    return combined[:limit]


if __name__ == "__main__":
    for topic in fetch_all_topics():
        print(f"[{topic.points} pts, {topic.source}] {topic.title} -> {topic.url}")

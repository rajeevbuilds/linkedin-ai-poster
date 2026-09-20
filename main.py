"""
Entry point: fetch a hot AI topic, draft a LinkedIn post, and (optionally)
publish it.

Safe by default: DRY_RUN=true in .env just prints the draft instead of
posting. Set DRY_RUN=false once you've tested it and trust the output.
"""
import json
import os
from datetime import datetime, timezone

from src import config
from src.topic_fetcher import fetch_hot_ai_topics
from src.content_generator import generate_post
from src.linkedin_client import publish_post

HISTORY_FILE = "data/posted_history.json"  # git-ignored


def _load_history() -> set:
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE) as f:
        return set(json.load(f))


def _save_history(history: set) -> None:
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(sorted(history), f, indent=2)


def run():
    history = _load_history()
    topics = fetch_hot_ai_topics(lookback_hours=config.TOPIC_LOOKBACK_HOURS, limit=10)
    fresh = [t for t in topics if t.url not in history]

    if not fresh:
        print("No fresh AI topics found right now. Try again later.")
        return

    topic = fresh[0]
    post_text = generate_post(topic)

    print("=" * 60)
    print(f"TOPIC: {topic.title}  ({topic.points} pts, {topic.source})")
    print("-" * 60)
    print(post_text)
    print("=" * 60)

    if config.DRY_RUN:
        print("\nDRY_RUN=true — nothing was posted. Set DRY_RUN=false in .env to publish for real.")
        return

    result = publish_post(post_text)
    print(f"\nPublished to LinkedIn. {result}")

    history.add(topic.url)
    _save_history(history)


if __name__ == "__main__":
    run()

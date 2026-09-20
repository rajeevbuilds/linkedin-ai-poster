"""
Ad-hoc LinkedIn posting: pass any text or idea as a command-line argument
and publish it directly, bypassing the automated topic fetcher.

Usage:
    python post_now.py "Your post text here"
    python post_now.py --draft "a rough idea to turn into a full post"
"""
import sys
from src import config
from src.linkedin_client import publish_post


def _draft_from_idea(idea: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        print("[post_now] No ANTHROPIC_API_KEY set — posting your idea as-is instead of drafting it.")
        return idea
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=(
            "You write short, engaging LinkedIn posts for a technical but "
            "broad professional audience. Style: confident, minimal emoji, "
            "3-6 short lines, end with a genuine question. Include 3-5 "
            "relevant hashtags on the last line."
        ),
        messages=[{"role": "user", "content": f"Write a LinkedIn post about: {idea}"}],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


def main():
    if len(sys.argv) < 2:
        print('Usage: python post_now.py "your text" OR python post_now.py --draft "your idea"')
        return

    if sys.argv[1] == "--draft":
        text = _draft_from_idea(" ".join(sys.argv[2:]))
    else:
        text = " ".join(sys.argv[1:])

    print("=" * 60)
    print(text)
    print("=" * 60)

    if config.DRY_RUN:
        print("\nDRY_RUN=true — nothing was posted. Set DRY_RUN=false in .env to publish for real.")
        return

    result = publish_post(text)
    print(f"\nPublished to LinkedIn. {result}")


if __name__ == "__main__":
    main()

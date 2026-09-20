"""
Turns a raw Topic into LinkedIn-ready post copy.

If ANTHROPIC_API_KEY is set, asks Claude to write a short, punchy post.
Otherwise falls back to a simple template so the app still works with zero
extra API keys.
"""
from src import config
from src.topic_fetcher import Topic

SYSTEM_PROMPT = (
    "You write short, engaging LinkedIn posts about AI news for a technical "
    "but broad professional audience. Style: confident, no hype-speak, no "
    "emojis spam (max 1-2), 3-6 short lines, end with a genuine question to "
    "spark discussion. Include 3-5 relevant hashtags on the last line. "
    "Never fabricate facts beyond what's given."
)


def _template_post(topic: Topic) -> str:
    return (
        f"🤖 Worth a look: {topic.title}\n\n"
        f"This has been getting attention in the AI community today "
        f"({topic.points} upvotes on {topic.source}).\n\n"
        f"Read more: {topic.url}\n\n"
        f"What's your take on this?\n\n"
        f"#AI #MachineLearning #TechNews #Innovation"
    )


def _claude_post(topic: Topic) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_prompt = (
        f"Write a LinkedIn post about this AI story:\n\n"
        f"Title: {topic.title}\n"
        f"Source: {topic.source} ({topic.points} points)\n"
        f"Link: {topic.url}\n\n"
        f"Include the link near the end of the post."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def generate_post(topic: Topic) -> str:
    if config.ANTHROPIC_API_KEY:
        try:
            return _claude_post(topic)
        except Exception as exc:  # fall back rather than crash the whole run
            print(f"[content_generator] Claude generation failed ({exc}); using template.")
    return _template_post(topic)

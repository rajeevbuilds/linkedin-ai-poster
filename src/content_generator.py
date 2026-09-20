"""
Turns a raw Topic into LinkedIn-ready post copy.

If ANTHROPIC_API_KEY is set, asks Claude to write a short, punchy post.
Otherwise falls back to a simple template so the app still works with zero
extra API keys.
"""
import json
import os
import random

from src import config
from src.topic_fetcher import Topic

LAST_CHOICES_FILE = "data/last_template_choices.json"  # git-ignored

SYSTEM_PROMPT = (
    "You write short, engaging LinkedIn posts about AI news for a technical "
    "but broad professional audience. Style: confident, no hype-speak, no "
    "emojis spam (max 1-2), 3-6 short lines, end with a genuine question to "
    "spark discussion. Include 3-5 relevant hashtags on the last line. "
    "Never fabricate facts beyond what's given."
)

OPENERS = [
    "🤖 Worth a look:",
    "💡 Just came across this:",
    "🔍 Interesting one today:",
    "📌 Flagging this:",
    "🚀 This caught my eye:",
    "⚡ Quick share:",
    "🧠 Been thinking about this:",
    "👀 Take a look at this:",
]

ATTENTION_PHRASES = [
    "This has been generating buzz in the AI community today",
    "This is making the rounds in AI circles right now",
    "People in tech are talking about this today",
    "This popped up on my radar today",
    "Seeing this get shared a lot today",
    "This is trending in AI discussions today",
    "This is picking up traction today",
    "There's some real discussion happening around this",
    "This one's sparking conversation today",
]

CLOSING_QUESTIONS = [
    "What's your take on this?",
    "Curious what others think here.",
    "Where do you land on this?",
    "Thoughts?",
    "Does this change anything for you?",
    "How are you thinking about this?",
]

HASHTAG_SETS = [
    "#AI #MachineLearning #TechNews #Innovation",
    "#ArtificialIntelligence #AI #TechTrends #FutureOfWork",
    "#AI #MachineLearning #Tech #Innovation #AINews",
]


def _load_last_choices() -> dict:
    if not os.path.exists(LAST_CHOICES_FILE):
        return {}
    try:
        with open(LAST_CHOICES_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_last_choices(choices: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(LAST_CHOICES_FILE, "w") as f:
        json.dump(choices, f, indent=2)


def _choose_excluding(options: list, last_used):
    remaining = [o for o in options if o != last_used]
    return random.choice(remaining or options)


def _template_post(topic: Topic) -> str:
    last = _load_last_choices()

    opener = _choose_excluding(OPENERS, last.get("opener"))
    attention_phrase = _choose_excluding(ATTENTION_PHRASES, last.get("attention_phrase"))
    closing_question = _choose_excluding(CLOSING_QUESTIONS, last.get("closing_question"))
    hashtag_set = _choose_excluding(HASHTAG_SETS, last.get("hashtag_set"))

    _save_last_choices({
        "opener": opener,
        "attention_phrase": attention_phrase,
        "closing_question": closing_question,
        "hashtag_set": hashtag_set,
    })

    attention_detail = (
        f"({topic.points} upvotes on {topic.source})"
        if topic.source == "Hacker News"
        else f"(via {topic.source})"
    )
    return (
        f"{opener} {topic.title}\n\n"
        f"{attention_phrase} {attention_detail}.\n\n"
        f"Read more: {topic.url}\n\n"
        f"{closing_question}\n\n"
        f"{hashtag_set}"
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

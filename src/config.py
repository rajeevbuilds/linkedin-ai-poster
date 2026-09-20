"""
All secrets are read from environment variables (populated from .env locally,
or from GitHub Actions "Secrets" in CI). Nothing sensitive is ever hardcoded
or written back to disk here.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # no-op in CI where .env doesn't exist; real env vars still work


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


LINKEDIN_CLIENT_ID = _get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = _get("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = _get("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
LINKEDIN_ACCESS_TOKEN = _get("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_AUTHOR_URN = _get("LINKEDIN_AUTHOR_URN")

ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")

GOOGLE_API_KEY = _get("GOOGLE_API_KEY")
GENERATE_IMAGE = _get("GENERATE_IMAGE", "true").lower() != "false"

TOPIC_LOOKBACK_HOURS = int(_get("TOPIC_LOOKBACK_HOURS", "24"))
DRY_RUN = _get("DRY_RUN", "true").lower() != "false"


def require(*names: str) -> None:
    """Fail loudly and early if required secrets are missing, instead of
    halfway through an API call."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Set them in your .env file (see .env.example)."
        )

"""
Minimal client for publishing to a personal LinkedIn profile via the UGC
Posts API — text-only, or with one attached image.

Requires an access token with the `w_member_social` scope — get one by
running `python -m src.oauth_helper` once.
"""
from typing import Optional

import requests

from src import config

API_BASE = "https://api.linkedin.com/v2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _register_image_upload() -> tuple[str, str]:
    """Step 1 of image posting: tell LinkedIn we want to upload an image.
    Returns (upload_url, asset_urn)."""
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": config.LINKEDIN_AUTHOR_URN,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    resp = requests.post(f"{API_BASE}/assets?action=registerUpload", headers=_headers(), json=payload, timeout=15)
    if resp.status_code >= 300:
        raise RuntimeError(f"LinkedIn upload registration failed {resp.status_code}: {resp.text}")

    data = resp.json()["value"]
    upload_url = data["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn = data["asset"]
    return upload_url, asset_urn


def _upload_image_bytes(upload_url: str, image_path: str) -> None:
    """Step 2: PUT the raw image bytes to the URL LinkedIn gave us."""
    with open(image_path, "rb") as f:
        resp = requests.put(
            upload_url,
            data=f,
            headers={"Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}"},
            timeout=30,
        )
    if resp.status_code >= 300:
        raise RuntimeError(f"LinkedIn image upload failed {resp.status_code}: {resp.text}")


def publish_post(text: str, image_path: Optional[str] = None) -> dict:
    """Publishes a text post, or a text+image post if image_path is given."""
    config.require("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN")

    share_content = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE",
    }

    if image_path:
        try:
            upload_url, asset_urn = _register_image_upload()
            _upload_image_bytes(upload_url, image_path)
            share_content["shareMediaCategory"] = "IMAGE"
            share_content["media"] = [{"status": "READY", "media": asset_urn}]
        except Exception as exc:
            # Don't lose the whole post over an image problem — fall back to text-only.
            print(f"[linkedin_client] Image attach failed ({exc}); posting text-only instead.")

    payload = {
        "author": config.LINKEDIN_AUTHOR_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(f"{API_BASE}/ugcPosts", headers=_headers(), json=payload, timeout=15)
    if resp.status_code >= 300:
        raise RuntimeError(f"LinkedIn API error {resp.status_code}: {resp.text}")
    return {"status_code": resp.status_code, "post_id": resp.headers.get("x-restli-id")}


def get_my_urn() -> str:
    """Helper to fetch the authenticated user's URN (needed for LINKEDIN_AUTHOR_URN)."""
    config.require("LINKEDIN_ACCESS_TOKEN")
    headers = {"Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}"}
    resp = requests.get(f"{API_BASE}/userinfo", headers=headers, timeout=15)
    resp.raise_for_status()
    sub = resp.json().get("sub")
    return f"urn:li:person:{sub}"

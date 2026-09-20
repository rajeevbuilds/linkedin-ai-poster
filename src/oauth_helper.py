"""
Run this ONCE to authorize the app against your own LinkedIn account and
obtain LINKEDIN_ACCESS_TOKEN. Paste the printed values into your .env file.

Requires LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET / LINKEDIN_REDIRECT_URI
to already be set in .env (from your LinkedIn Developer App).

Usage:
    python src/oauth_helper.py
"""
import http.server
import threading
import urllib.parse
import webbrowser

import requests

from src import config, linkedin_client

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "openid profile w_member_social"

_auth_code = {"value": None}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _auth_code["value"] = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Authorized. You can close this tab and return to the terminal.</h2>")

    def log_message(self, *args):
        pass  # keep console clean


def _run_local_server(port: int):
    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.handle_request()  # handle exactly one request, then stop


def main():
    config.require("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI")

    redirect_uri = config.LINKEDIN_REDIRECT_URI
    port = int(urllib.parse.urlparse(redirect_uri).port or 8000)

    server_thread = threading.Thread(target=_run_local_server, args=(port,), daemon=True)
    server_thread.start()

    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": config.LINKEDIN_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
    })
    auth_url = f"{AUTH_URL}?{query}"
    print(f"Opening browser for LinkedIn authorization:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server_thread.join(timeout=120)
    code = _auth_code["value"]
    if not code:
        raise RuntimeError("No authorization code received (timed out or denied).")

    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": config.LINKEDIN_CLIENT_ID,
        "client_secret": config.LINKEDIN_CLIENT_SECRET,
    }, timeout=15)
    resp.raise_for_status()
    token_data = resp.json()
    access_token = token_data["access_token"]

    print("\nSUCCESS. Add these to your .env file:\n")
    print(f"LINKEDIN_ACCESS_TOKEN={access_token}")

    # Now fetch the author URN using the fresh token
    config.LINKEDIN_ACCESS_TOKEN = access_token
    try:
        urn = linkedin_client.get_my_urn()
        print(f"LINKEDIN_AUTHOR_URN={urn}")
    except Exception as exc:
        print(f"(Could not auto-fetch author URN: {exc}. Add LINKEDIN_AUTHOR_URN manually.)")


if __name__ == "__main__":
    main()

# LinkedIn AI Poster

Finds a trending AI story, drafts a LinkedIn post about it, and publishes it
to your profile — manually or on an automatic daily schedule. Built to be
safe-by-default: it will only *print* a draft until you explicitly turn on
posting.

**Nothing sensitive lives in this repo.** All keys/tokens are read from
environment variables (`.env` locally, GitHub Secrets in automation), and
`.gitignore` excludes `.env` and any credential/data files from ever being
committed.

## How it works

```
topic_fetcher.py   → finds a "hot" AI story (Hacker News, filtered by keywords)
content_generator.py → drafts LinkedIn-ready copy (Claude if you have a key, else a template)
linkedin_client.py → publishes the post via LinkedIn's API
main.py            → ties it together, skips topics already posted
```

## 1. Set up locally

```bash
git clone <your-repo-url>
cd linkedin-ai-poster
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
```

## 2. Create a LinkedIn Developer App (required to post via API)

1. Go to https://www.linkedin.com/developers/apps → **Create app**.
2. Fill in the basic details (you'll need a LinkedIn Company Page to attach
   it to — you can create a minimal one if you don't have one).
3. Under **Products**, request **"Share on LinkedIn"** and **"Sign In with
   LinkedIn using OpenID Connect"**. "Share on LinkedIn" may require review —
   for personal testing it's often auto-approved within minutes, but it can
   take longer.
4. Under **Auth**, add a redirect URL: `http://localhost:8000/callback`
   (must exactly match `LINKEDIN_REDIRECT_URI` in your `.env`).
5. Copy the **Client ID** and **Client Secret** into your `.env`.

## 3. Authorize your account (one-time)

This runs a local OAuth flow, opens your browser to approve access, and
prints the token you need:

```bash
python -m src.oauth_helper
```

Copy the printed `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_AUTHOR_URN` into
`.env`. (LinkedIn access tokens typically expire after ~60 days — rerun this
when it does.)

## 4. (Optional) Add an Anthropic API key

If `ANTHROPIC_API_KEY` is set in `.env`, posts are drafted by Claude for
better quality. Without it, a simple template is used instead — the app
works either way. Get a key at https://console.anthropic.com.

## 4b. (Optional) Add a Google API key for post images

Set `GOOGLE_API_KEY` in `.env` to have each post generated with an
accompanying image, using Google's Gemini image-generation model
(`gemini-2.5-flash-image`). Get a free key at
https://aistudio.google.com/apikey.

Note: Claude itself doesn't generate images — this uses Google's model
specifically for that step, while Claude (if configured) still writes the
post text. Set `GENERATE_IMAGE=false` in `.env` to skip images and post
text-only, which also works fine with no Google key at all. If image
generation fails for any reason, the app automatically falls back to
posting text-only rather than failing the whole run.

## 5. Test it (safe — won't actually post)

```bash
python main.py
```

With the default `DRY_RUN=true`, this prints the topic and drafted post
without publishing anything. Read it over.

## 6. Go live

Once you're happy with the output, set `DRY_RUN=false` in `.env` and run
`python main.py` again — this time it publishes to your LinkedIn profile.

## 7. Push this repo to GitHub (code only — no secrets)

```bash
git add .
git commit -m "Initial commit: LinkedIn AI poster"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.env`, tokens, and any local data files are excluded by `.gitignore` and
will not be part of this push — verify with `git status` before committing
if you ever want to double check.

## 8. (Optional) Fully automate with GitHub Actions

A workflow at `.github/workflows/daily_post.yml` is already included and
runs the poster once a day. To enable it:

1. In your GitHub repo, go to **Settings → Secrets and variables → Actions**.
2. Add these repository secrets:
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_AUTHOR_URN`
   - `ANTHROPIC_API_KEY` (optional — better post text)
   - `GOOGLE_API_KEY` (optional — adds an image to each post)
3. That's it — it'll run on the schedule in the workflow file (edit the
   `cron` line to change the time), or you can trigger it manually from the
   **Actions** tab.

## Notes & limits

- LinkedIn's API for personal-profile posting is tightly scoped
  (`w_member_social`) and access tokens expire periodically — this isn't a
  workaround for that, just automation on top of a properly authorized app.
- Posting frequency: don't post too often from one account — LinkedIn can
  flag accounts for spam-like automated behavior. Once a day is a reasonable
  starting point.
- `main.py` keeps a local `data/posted_history.json` (git-ignored) so it
  doesn't repost the same story twice.

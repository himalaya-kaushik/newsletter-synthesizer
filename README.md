# newsletter-synthesizer

Fetches newsletters from a dedicated Gmail inbox via IMAP, converts them to clean markdown, and writes them into an Obsidian vault. A GitHub Action (living in your private vault repo) runs it daily at 07:30 IST.

Synthesis is a separate manual step — see `for-vault/CLAUDE.md`.

## How it works

1. Connects to `imap.gmail.com:993` using an app password.
2. On the first run, fetches emails from the last 24 hours. On subsequent runs, fetches only emails newer than the last processed UID (tracked in `STATE_FILE`).
3. Converts each email's HTML (or plain-text) body to clean markdown via `markdownify`, stripping tracking pixels, images, scripts, and footer boilerplate.
4. Writes each email to `{NEWSLETTERS_DIR}/{YYYY-MM-DD}/{sender}--{subject}.md` with YAML frontmatter.
5. Skips files that already exist (idempotent).
6. Saves the highest UID seen to `STATE_FILE` for the next run.

The script **never runs git commands** — that's the Action's job.

## Local test

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export environment variables
export GMAIL_ADDRESS=kaushik.himalaya143@gmail.com
export GMAIL_APP_PASSWORD=<your-16-char-app-password>
export NEWSLETTERS_DIR=/Users/himalaya/Desktop/Himalaya/Notes/Newsletters
export STATE_FILE=/Users/himalaya/Desktop/Himalaya/Notes/.newsletter_state.json

# 3. Run
python fetch_newsletters.py
```

Generate an app password at: https://myaccount.google.com/apppasswords  
(Requires 2-Step Verification to be enabled on the account.)

## Deploy to your vault repo

1. Copy `for-vault/.github/workflows/daily.yml` → `.github/workflows/daily.yml` in your `himalaya-vault` private repo.
2. Copy `for-vault/CLAUDE.md` → `CLAUDE.md` in your `himalaya-vault` private repo.
3. Add two repository secrets in the vault repo's Settings → Secrets and variables → Actions:
   - `GMAIL_ADDRESS` — your Gmail address
   - `GMAIL_APP_PASSWORD` — your 16-character app password
4. The Action runs automatically every day at **07:30 IST** (02:30 UTC) and can also be triggered manually from the **Actions** tab via "Run workflow".

The Action clones this public repo at runtime, so there is nothing to update in the vault repo when you change the script — just push here.

## Synthesis

After the Action runs, open your vault in Claude Code and it will follow `CLAUDE.md` to synthesize today's `Newsletters/YYYY-MM-DD/` folder into `Briefs/YYYY-MM-DD.md`.

## File layout

```
newsletter-synthesizer/
├── fetch_newsletters.py   # main script
├── requirements.txt
├── README.md
└── for-vault/
    ├── CLAUDE.md                          # copy into vault root
    └── .github/workflows/daily.yml       # copy into vault repo
```

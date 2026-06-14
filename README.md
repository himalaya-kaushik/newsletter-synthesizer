# newsletter-synthesizer

**Your inbox reads ten AI newsletters so you don't have to.**

I subscribe to too many AI/ML newsletters. Every morning the same five stories
show up across all of them, wrapped in different "this changes everything"
packaging. Reading them all is a waste; reading none of them means missing
things. So I built a small machine to do the boring half.

This is that machine. It is a personal tool, not a product. No roadmap, no
support, no uptime promises. If it breaks, I fix it when I feel like it. You are
very welcome to steal it.

---

## The one idea worth stealing

Most "AI summarizer" tools summarize each email and hand you ten summaries. That
is just your inbox with extra steps.

This does the opposite. It treats **redundancy as signal**: if a story shows up
in eight newsletters, that is not eight things to read — it is *one* thing, and
the fact that eight editors picked it up is the loudest possible hint that it
matters. So overlapping coverage gets collapsed into a single item and the number
of sources becomes the ranking. Synthesis, not summary.

The actual intelligence lives in a [`CLAUDE.md`](for-vault/CLAUDE.md) rubric you
run on demand — so the automated half stays dumb (zero LLM calls, nothing to rot)
and the smart half only runs when you actually want to catch up. Fork the rubric,
swap in your own interests, point it at your own newsletters.

---

## How it works

1. Connects to a Gmail inbox over IMAP (`imap.gmail.com:993`) with an app password.
2. First run grabs the last day of mail; after that it only fetches messages newer
   than the last one it saw (tracked by IMAP UID in a small state file).
3. Converts each email's HTML to clean markdown with `html2text` — flattening the
   nested layout tables newsletters are built from, dropping images, tracking
   pixels, scripts, link URLs, and footer junk.
4. Writes each one to `Newsletters/YYYY-MM-DD/{sender}--{subject}.md` with a bit
   of YAML frontmatter.
5. Skips anything it already wrote (safe to re-run).

It **never touches git** — committing and pushing is the GitHub Action's job. The
script just makes files.

> Works best with a dedicated Gmail account subscribed to *only* newsletters.
> Then the whole inbox is in scope and you don't need filters or labels.

---

## Try it locally

```bash
# 1. install
pip install -r requirements.txt

# 2. point it at your stuff
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="your-16-char-app-password"
export NEWSLETTERS_DIR="/path/to/your/vault/Newsletters"
export STATE_FILE="/path/to/your/vault/.newsletter_state.json"

# 3. go
python fetch_newsletters.py
```

App password: https://myaccount.google.com/apppasswords
(needs 2-Step Verification on the account first).

---

## Run it every morning

The whole thing is designed to live in a **private** repo that doubles as your
notes vault, so the daily action commits straight into it.

1. Copy `for-vault/.github/workflows/daily.yml` into your private vault repo at
   `.github/workflows/daily.yml`.
2. Copy `for-vault/CLAUDE.md` into the root of that repo.
3. Add two repo secrets (Settings → Secrets and variables → Actions):
   `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`.
4. Done. It runs daily at **07:30 IST** (02:30 UTC) and you can trigger it by hand
   from the **Actions** tab.

The action clones this public repo at runtime, so when you tweak the script you
just push here — nothing to update in the vault repo.

If you keep your vault in [Obsidian](https://obsidian.md), the Obsidian Git plugin
pulls each morning's fetch down to your machine automatically.

---

## The smart half

Once the day's newsletters are sitting in your vault, open it in Claude Code and
let it follow `CLAUDE.md` — it reads `Newsletters/YYYY-MM-DD/`, collapses the
overlap, ranks by how many sources ran each story, filters to what you actually
care about, and writes a two-minute brief to `Briefs/YYYY-MM-DD.md`.

Edit the `YOUR LENS` block in `CLAUDE.md` to make it yours. That's the only part
you need to change.

---

## Layout

```
newsletter-synthesizer/
├── fetch_newsletters.py            # the dumb half: fetch + clean + write
├── requirements.txt
├── README.md
└── for-vault/                      # the bits that live in your private vault repo
    ├── CLAUDE.md                   # the smart half: synthesis rubric
    └── .github/workflows/daily.yml # the cron
```

---

Built for an audience of one. Have fun.

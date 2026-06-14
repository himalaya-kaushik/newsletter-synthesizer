#!/usr/bin/env python3
"""
fetch_newsletters.py

Connects to a Gmail inbox via IMAP, downloads new emails, converts them to
clean markdown, and writes them into an Obsidian vault directory.

Required environment variables:
    GMAIL_ADDRESS      - Gmail account (e.g. you@gmail.com)
    GMAIL_APP_PASSWORD - Gmail app password (not your account password)
    NEWSLETTERS_DIR    - Path to the folder where markdown files are written
    STATE_FILE         - Path to a JSON file that stores the last processed UID
"""

import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import html2text
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    required = ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "NEWSLETTERS_DIR", "STATE_FILE"]
    config = {}
    missing = []
    for key in required:
        val = os.environ.get(key)
        if not val:
            missing.append(key)
        config[key] = val
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return config


# ---------------------------------------------------------------------------
# State (last processed UID)
# ---------------------------------------------------------------------------

def load_last_uid(state_file: str) -> int | None:
    path = Path(state_file)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return int(data.get("last_uid", 0)) or None
    except (json.JSONDecodeError, ValueError):
        return None


def save_last_uid(state_file: str, uid: int) -> None:
    Path(state_file).write_text(json.dumps({"last_uid": uid}, indent=2))


# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def connect(address: str, password: str) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    conn.login(address, password)
    conn.select("INBOX", readonly=True)
    return conn


def fetch_new_uids(conn: imaplib.IMAP4_SSL, last_uid: int | None) -> list[int]:
    """Return UIDs of messages we haven't processed yet, oldest first."""
    if last_uid is not None:
        status, data = conn.uid("SEARCH", None, f"UID {last_uid + 1}:*")
        if status != "OK" or not data or not data[0]:
            return []
        raw_uids = [int(u) for u in data[0].split() if u]
        uids = [u for u in raw_uids if u > last_uid]
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = conn.uid("SEARCH", None, f"SINCE {since}")
        if status != "OK" or not data or not data[0]:
            return []
        uids = [int(u) for u in data[0].split() if u]

    return sorted(uids)


def fetch_raw_message(conn: imaplib.IMAP4_SSL, uid: int) -> bytes | None:
    status, data = conn.uid("FETCH", str(uid), "(RFC822)")
    if status != "OK" or not data or data[0] is None:
        return None
    # data[0] is (b'1 (RFC822 {size}', b'<raw bytes>')
    return data[0][1] if isinstance(data[0], tuple) else None


# ---------------------------------------------------------------------------
# Email parsing
# ---------------------------------------------------------------------------

def decode_header_value(raw: str | bytes | None) -> str:
    """Decode an RFC-2047-encoded header value to a plain string."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded).strip()


def get_text_body(msg) -> tuple[str, str]:
    """
    Return (body_text, mime_type) preferring text/html over text/plain.
    mime_type is 'html' or 'plain'.
    """
    html_body = None
    plain_body = None

    for part in msg.walk():
        ct = part.get_content_type()
        cd = str(part.get("Content-Disposition", ""))
        if "attachment" in cd:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if ct == "text/html" and html_body is None:
            html_body = text
        elif ct == "text/plain" and plain_body is None:
            plain_body = text

    if html_body:
        return html_body, "html"
    return plain_body or "", "plain"


# ---------------------------------------------------------------------------
# HTML → Markdown conversion and cleanup
# ---------------------------------------------------------------------------


_ZERO_WIDTH = re.compile(r"[‌​﻿]+")


def strip_noise_from_html(html: str) -> str:
    """Remove scripts, hidden elements, and zero-width chars before conversion."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    for tag in soup.find_all("img"):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.get("src", "").startswith("data:") or tag.get("href", "").startswith("data:"):
            tag.decompose()

    for tag in soup.find_all(style=True):
        style = tag["style"].replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()

    
    for text_node in soup.find_all(string=True):
        cleaned = _ZERO_WIDTH.sub("", text_node)
        if cleaned != text_node:
            text_node.replace_with(cleaned)

    return str(soup)


_FOOTER_PATTERNS = [
    re.compile(r"(?im)^.*unsubscribe.*$"),
    re.compile(r"(?im)^.*view (this email|in (your )?browser).*$"),
    re.compile(r"(?im)^.*you('re| are) receiving this.*$"),
    re.compile(r"(?im)^.*you received this (email|newsletter|message).*$"),
    re.compile(r"(?im)^.*(manage|update) (your )?(email )?preferences.*$"),
    re.compile(r"(?im)^.*©\s*\d{4}.*$"),
    re.compile(r"(?im)^.*(privacy policy|terms of (service|use)).*$"),
    re.compile(r"(?im)^.*add (us|.+) to your address book.*$"),
    re.compile(r"(?im)^.*228 Park.*$"),
    re.compile(r"(?im)^\s*https?://\S+\s*$"),
    re.compile(r"(?im)^.*click below to let me know.*$"),
    re.compile(r"(?im)^.*exceeded expectations.*$"),
    re.compile(r"(?im)^.*not feeling it.*$"),
    re.compile(r"(?im)^.*pretty average.*$"),
]

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _strip_links(md: str) -> str:
    """Drop all URLs from markdown links; keep visible text, drop empty links."""
    def replace(m: re.Match) -> str:
        text = m.group(1).strip()
        return text  # empty string drops the whole token

    return _MD_LINK.sub(replace, md)


def clean_markdown(md: str) -> str:
    """Post-process converted text: strip links, footer junk, collapse blank lines."""
    md = _strip_links(md)

    for pattern in _FOOTER_PATTERNS:
        md = pattern.sub("", md)

    md = re.sub(r"\n{4,}", "\n\n", md)

    lines = []
    for ln in md.splitlines():
        if _ZERO_WIDTH.sub("", ln).strip() == "":
            continue
        lines.append(ln)

    return "\n".join(lines).strip()


def html_to_markdown(html: str) -> str:
    clean_html = strip_noise_from_html(html)

    h = html2text.HTML2Text()
    h.ignore_tables = True   
    h.ignore_images = True
    h.body_width = 0            
    h.ignore_links = False
    h.ignore_emphasis = False

    md = h.handle(clean_html)
    return clean_markdown(md)


def plain_to_markdown(text: str) -> str:
    """Minimal cleanup for plain-text emails."""
    md = re.sub(r"\r\n", "\n", text)
    md = re.sub(r"\n{3,}", "\n\n", md)
    for pattern in _FOOTER_PATTERNS:
        md = pattern.sub("", md)
    return md.strip()


# ---------------------------------------------------------------------------
# Filename / path helpers
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """Lowercase, collapse non-alphanumeric runs to hyphens, truncate."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_len].rstrip("-")


def email_date(msg) -> datetime:
    """Parse the Date header; fall back to now if unparseable."""
    raw = msg.get("Date", "")
    try:
        ts = email.utils.parsedate_to_datetime(raw)
        return ts.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def sender_name(msg) -> str:
    """Return the display name (or address) of the sender, slugified."""
    from_raw = decode_header_value(msg.get("From", "unknown"))
    name, addr = email.utils.parseaddr(from_raw)
    label = name if name else addr.split("@")[0]
    return slugify(label, max_len=40)


def output_path(newsletters_dir: str, msg) -> Path:
    dt = email_date(msg)
    date_str = dt.strftime("%Y-%m-%d")
    subject = decode_header_value(msg.get("Subject", "no-subject"))
    filename = f"{sender_name(msg)}--{slugify(subject)}.md"
    return Path(newsletters_dir) / date_str / filename


# ---------------------------------------------------------------------------
# Frontmatter + file writing
# ---------------------------------------------------------------------------

def build_frontmatter(msg) -> str:
    from_raw = decode_header_value(msg.get("From", ""))
    subject = decode_header_value(msg.get("Subject", ""))
    dt = email_date(msg)
    message_id = msg.get("Message-ID", "").strip()

    # Escape double-quotes in YAML values.
    def esc(s: str) -> str:
        return s.replace('"', '\\"')

    return (
        "---\n"
        f'sender: "{esc(from_raw)}"\n'
        f'subject: "{esc(subject)}"\n'
        f'date: "{dt.strftime("%Y-%m-%dT%H:%M:%SZ")}"\n'
        f'message_id: "{esc(message_id)}"\n'
        "---\n\n"
    )


def write_newsletter(path: Path, msg) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body_text, mime_type = get_text_body(msg)
    if mime_type == "html":
        body_md = html_to_markdown(body_text)
    else:
        body_md = plain_to_markdown(body_text)

    content = build_frontmatter(msg) + body_md
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config = load_config()
    last_uid = load_last_uid(config["STATE_FILE"])

    print(f"Connecting to imap.gmail.com as {config['GMAIL_ADDRESS']} …")
    conn = connect(config["GMAIL_ADDRESS"], config["GMAIL_APP_PASSWORD"])

    uids = fetch_new_uids(conn, last_uid)
    if not uids:
        print("Fetched 0 new newsletters.")
        conn.logout()
        return

    fetched = 0
    skipped = 0
    max_uid = last_uid or 0

    for uid in uids:
        raw = fetch_raw_message(conn, uid)
        if raw is None:
            continue

        msg = email.message_from_bytes(raw)
        path = output_path(config["NEWSLETTERS_DIR"], msg)

        if path.exists():
            skipped += 1
        else:
            write_newsletter(path, msg)
            fetched += 1

        max_uid = max(max_uid, uid)

    conn.logout()

    if max_uid > (last_uid or 0):
        save_last_uid(config["STATE_FILE"], max_uid)

    summary_parts = [f"Fetched {fetched} new newsletter{'s' if fetched != 1 else ''}."]
    if skipped:
        summary_parts.append(f"Skipped {skipped} already-existing file{'s' if skipped != 1 else ''}.")
    print(" ".join(summary_parts))


if __name__ == "__main__":
    main()

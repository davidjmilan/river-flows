#!/usr/bin/env python3
"""
Scrape current flow (CFS) for the two Deerfield River sections that have no
public API or historical time series, and append each reading to a rolling
JSON history file. Run on a schedule by GitHub Actions.

Sources publish only a single "current" value, so the weekly history is built
up over time, one reading per run.
"""

import json
import os
import re
import ssl
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RETENTION_DAYS = 8          # keep slightly more than a week
REQUEST_TIMEOUT = 30        # seconds


def _ssl_context():
    """
    Build a verifying SSL context. Some Python installs (notably python.org
    builds on macOS) ship without access to a system CA bundle, causing
    CERTIFICATE_VERIFY_FAILED. If the `certifi` package is available, point at
    its bundle so verification works without weakening security.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()

# A normal browser UA; some hosts reject the default urllib agent.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

RIVERS = [
    {
        "id": "upper-deerfield",
        "name": "Upper Deerfield (Fife Brook)",
        "url": "https://safewaters.com/facility/fife-brook/",
        # e.g. "133.42 cfs as of 2026-06-12 10:00:00 AM (EDT)"
        "pattern": re.compile(r"([\d,]+(?:\.\d+)?)\s*cfs\b", re.IGNORECASE),
    },
    {
        "id": "dryway",
        "name": "Dryway (Deerfield #5)",
        "url": "http://www.h2oline.com/srcs/255122.html",
        # e.g. "the total flow below the dam was 84 CFS."
        "pattern": re.compile(r"was\s+([\d,]+(?:\.\d+)?)\s*CFS", re.IGNORECASE),
    },
]


def fetch(url: str) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=REQUEST_TIMEOUT, context=SSL_CONTEXT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def parse_value(html: str, pattern: re.Pattern):
    m = pattern.search(html)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def load_history(path: str):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def prune(history, cutoff: datetime):
    kept = []
    for pt in history:
        try:
            t = datetime.fromisoformat(pt["t"])
        except (KeyError, ValueError):
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if t >= cutoff:
            kept.append(pt)
    return kept


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=RETENTION_DAYS)
    exit_code = 0

    for river in RIVERS:
        path = os.path.join(DATA_DIR, f"{river['id']}.json")
        history = prune(load_history(path), cutoff)

        try:
            html = fetch(river["url"])
            value = parse_value(html, river["pattern"])
            if value is None:
                print(f"[WARN] {river['id']}: flow value not found in page", file=sys.stderr)
                exit_code = 1
            else:
                history.append({"t": now.isoformat(timespec="seconds"), "v": value})
                print(f"[OK]   {river['id']}: {value} CFS")
        except (URLError, HTTPError, ValueError) as e:
            # Don't fail the whole job for one flaky source; keep existing history.
            print(f"[WARN] {river['id']}: fetch failed: {e}", file=sys.stderr)
            exit_code = 1

        # Always rewrite (prunes old points even when the fetch failed).
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=0, separators=(",", ":"))
            f.write("\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

"""
core.py: shared plumbing for the intelligence pipeline.

Everything here is domain-agnostic. It knows how to be a polite network
citizen (rate limiting + robots.txt), how to give every ingested item a
stable deduplication key, and how to write items to the corpus in one
normalized markdown shape. Source adapters (pipeline/sources/*) depend on
this module; this module depends on nothing in the project.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

USER_AGENT = "intel-forge/1.0 (+https://gitlab.com/your-org/intel-forge)"

# Where normalized items land. Overridable via env so the scheduler and the
# freshness checker can agree on one location without hard-coding a path.
CORPUS_DIR = Path(os.getenv("CORPUS_DIR", Path(__file__).resolve().parent.parent / "corpus"))


# ---------------------------------------------------------------------------
# The unit of intelligence
# ---------------------------------------------------------------------------

@dataclass
class Item:
    """One normalized piece of intelligence, whatever the source.

    `source` is the adapter key (e.g. "rss:acme-blog"). `identifier` is the
    most stable native ID the source exposes (a GUID, a CVE number, a
    canonical URL); it is what dedup keys off, so prefer something that does
    not change between runs. Everything else is presentation.
    """
    source: str
    identifier: str
    title: str
    url: str = ""
    published: str = ""          # ISO date if you can get it; free text is fine
    author: str = ""
    content_md: str = ""
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Politeness: per-domain rate limiting + robots.txt
# ---------------------------------------------------------------------------

class RateLimiter:
    """Enforce a minimum delay between requests to the *same* domain.

    Different domains proceed independently; two slow sources don't block each
    other, but you never hammer one host.
    """

    def __init__(self, default_delay: float = 1.0):
        self.default_delay = default_delay
        self._last: dict[str, float] = {}

    def wait(self, url: str, delay: Optional[float] = None) -> None:
        domain = urlparse(url).netloc
        gap = self.default_delay if delay is None else delay
        now = time.monotonic()
        prev = self._last.get(domain)
        if prev is not None:
            elapsed = now - prev
            if elapsed < gap:
                time.sleep(gap - elapsed)
        self._last[domain] = time.monotonic()


class RobotsCache:
    """Cache one robots.txt parser per domain and answer can_fetch()."""

    def __init__(self, user_agent: str = USER_AGENT):
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._parsers.get(domain)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{domain}/robots.txt")
            try:
                rp.read()
            except Exception:
                # If robots.txt is unreachable, default to allowed but stay
                # rate-limited. Tighten this to `return False` if you'd rather
                # fail closed.
                self._parsers[domain] = rp
                return True
            self._parsers[domain] = rp
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True


# ---------------------------------------------------------------------------
# Identity + filenames
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_len]


def stable_id(source: str, identifier: str) -> str:
    """Short, deterministic hash used as the dedup key and filename infix.

    Same (source, identifier) → same id on every run, so re-ingesting an item
    overwrites rather than duplicates.
    """
    raw = f"{source}::{identifier}"
    return hashlib.sha1(raw.encode()).hexdigest()[:10]


def corpus_path(item: Item) -> Path:
    sid = stable_id(item.source, item.identifier)
    # Keep the source's ":" out of the filename.
    src = item.source.replace(":", "-").replace("/", "-")
    name = f"{src}__{sid}__{slugify(item.title)}.md"
    return CORPUS_DIR / name


def already_have(item: Item) -> bool:
    return corpus_path(item).exists()


# ---------------------------------------------------------------------------
# Relevance filter (config-driven, domain-agnostic)
# ---------------------------------------------------------------------------

def is_relevant(text: str, include: list[str], exclude: list[str]) -> bool:
    """Cheap keyword gate.

    `include`: at least one must appear (empty list = accept anything).
    `exclude`: none may appear.
    Case-insensitive substring match; deliberately simple. Swap in embeddings
    or an LLM classifier here if your domain needs semantic filtering.
    """
    t = text.lower()
    if exclude and any(term.lower() in t for term in exclude):
        return False
    if not include:
        return True
    return any(term.lower() in t for term in include)


# ---------------------------------------------------------------------------
# Writing to the corpus
# ---------------------------------------------------------------------------

def write_item(item: Item, dry_run: bool = False) -> Optional[Path]:
    """Persist one item as normalized markdown. Returns the path (or None on dry-run)."""
    path = corpus_path(item)
    if dry_run:
        print(f"  [dry-run] would write: {path.name}")
        return None

    path.parent.mkdir(parents=True, exist_ok=True)

    meta_rows = [
        f"| Source | {item.source} |",
        f"| Identifier | {item.identifier} |",
        f"| Original URL | {item.url} |",
        f"| Published | {item.published or 'Unknown'} |",
        f"| Author | {item.author or 'Unknown'} |",
        f"| Ingested | {datetime.now(timezone.utc).strftime('%Y-%m-%d')} |",
    ]
    for k, v in item.extra.items():
        meta_rows.append(f"| {k} | {v} |")
    meta_block = "\n".join(meta_rows)

    text = f"""# [{item.source}] {item.title}

## Metadata
| Field | Value |
|---|---|
{meta_block}

## Content

{item.content_md}
"""
    path.write_text(text, encoding="utf-8")
    return path

"""
rss.py — generic RSS / Atom adapter (EXAMPLE).

Works with any feed. Configure instances in sources.yaml:

  - name: acme-blog
    type: rss
    url: https://blog.example.com/feed/
    # optional:
    author_fallback: "Acme"

This is one of three reference adapters shipped with the template. It is not
special — copy it as a starting point for your own sources.
"""

from __future__ import annotations

from typing import Iterable, Optional

from pipeline.core import Item, USER_AGENT

try:
    import feedparser
except ImportError:  # pragma: no cover
    feedparser = None

from pipeline.sources.base import Source


class RSSSource(Source):
    key = "rss"

    def fetch(self, since: Optional[str] = None) -> Iterable[Item]:
        if feedparser is None:
            raise RuntimeError("feedparser not installed. `pip install feedparser`")

        name = self.config["name"]
        url = self.config["url"]
        author_fallback = self.config.get("author_fallback", "")

        # feedparser fetches internally; respect robots + rate limit first.
        if not self.robots.can_fetch(url):
            print(f"  [robots] blocked: {url}")
            return
        self.rl.wait(url)

        parsed = feedparser.parse(url, agent=USER_AGENT)
        for entry in parsed.entries:
            published = _entry_date(entry)
            if since and published and published < since:
                continue
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            identifier = entry.get("id") or link or title
            content = _entry_content(entry)
            yield Item(
                source=f"rss:{name}",
                identifier=identifier,
                title=title or "(untitled)",
                url=link,
                published=published,
                author=entry.get("author", author_fallback),
                content_md=content,
            )


def _entry_date(entry) -> str:
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            # Prefer the parsed struct if present for a clean ISO date.
            pt = entry.get(key + "_parsed")
            if pt:
                return f"{pt.tm_year:04d}-{pt.tm_mon:02d}-{pt.tm_mday:02d}"
            return val
    return ""


def _entry_content(entry) -> str:
    if entry.get("content"):
        return entry["content"][0].get("value", "")
    return entry.get("summary", "")

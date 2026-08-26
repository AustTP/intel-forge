"""
sitemap.py: generic sitemap adapter (EXAMPLE).

For sites without a feed. Reads a sitemap.xml, optionally filters URLs by a
substring, fetches each page, and stores a text-converted copy. Configure:

  - name: example-site
    type: sitemap
    url: https://www.example.com/sitemap.xml
    url_contains: /research/     # optional: only URLs containing this
    limit: 50                    # optional: cap pages per run (default 100)

Fetching full HTML pages is heavier and more fragile than a feed. Prefer rss
or rest_json when a source offers them. Respect the target's robots.txt (this
adapter does) and keep the rate limit conservative.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from pipeline.core import Item, USER_AGENT

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import html2text
    _H2T = html2text.HTML2Text()
    _H2T.ignore_links = False
    _H2T.body_width = 0
except ImportError:  # pragma: no cover
    _H2T = None

from pipeline.sources.base import Source

_LOC_RE = re.compile(r"<loc>(.*?)</loc>", re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class SitemapSource(Source):
    key = "sitemap"

    def fetch(self, since: Optional[str] = None) -> Iterable[Item]:
        if requests is None:
            raise RuntimeError("requests not installed. `pip install requests`")

        name = self.config["name"]
        sitemap_url = self.config["url"]
        contains = self.config.get("url_contains", "")
        limit = int(self.config.get("limit", 100))

        urls = self._read_sitemap(sitemap_url, contains, limit)
        for page_url in urls:
            if not self.robots.can_fetch(page_url):
                continue
            self.rl.wait(page_url)
            try:
                resp = requests.get(page_url, headers={"User-Agent": USER_AGENT}, timeout=20)
                resp.raise_for_status()
                html = resp.text
            except Exception as e:  # noqa: BLE001
                print(f"  [WARN] {name}: {page_url} → {e}")
                continue

            title_m = _TITLE_RE.search(html)
            title = (title_m.group(1).strip() if title_m else page_url)
            content = _H2T.handle(html).strip() if _H2T else html
            yield Item(
                source=f"sitemap:{name}",
                identifier=page_url,
                title=title,
                url=page_url,
                content_md=content,
            )

    def _read_sitemap(self, sitemap_url: str, contains: str, limit: int) -> list[str]:
        if not self.robots.can_fetch(sitemap_url):
            print(f"  [robots] blocked: {sitemap_url}")
            return []
        self.rl.wait(sitemap_url)
        try:
            resp = requests.get(sitemap_url, headers={"User-Agent": USER_AGENT}, timeout=20)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] sitemap {sitemap_url}: {e}")
            return []
        locs = _LOC_RE.findall(resp.text)
        if contains:
            locs = [u for u in locs if contains in u]
        return locs[:limit]

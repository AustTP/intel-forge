"""
rest_json.py: generic REST / JSON API adapter (EXAMPLE).

For sources that expose a JSON list endpoint. You tell it, via sources.yaml,
which JSON fields map to Item fields using simple dotted paths. Example:

  - name: example-api
    type: rest_json
    url: https://api.example.com/v1/items
    items_path: data.results        # dotted path to the list (blank = top-level list)
    map:
      identifier: id
      title: attributes.title
      url: links.self
      published: attributes.created_at
      author: attributes.author.name
      content_md: attributes.body
    # optional query params merged into the request:
    params:
      page_size: 100
    # optional: env var name holding a bearer token
    auth_env: EXAMPLE_API_TOKEN

Pagination varies wildly between APIs, so this reference adapter fetches a
single page. Override `fetch()` in a subclass for cursor/offset pagination.
See docs/ADDING_A_SOURCE.md.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional

from pipeline.core import Item, USER_AGENT

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

from pipeline.sources.base import Source


def _dig(obj: Any, dotted: str) -> Any:
    """Walk a dotted path like 'attributes.author.name' through nested dicts."""
    if not dotted:
        return obj
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


class RestJSONSource(Source):
    key = "rest_json"

    def fetch(self, since: Optional[str] = None) -> Iterable[Item]:
        if requests is None:
            raise RuntimeError("requests not installed. `pip install requests`")

        name = self.config["name"]
        url = self.config["url"]
        items_path = self.config.get("items_path", "")
        field_map = self.config.get("map", {})
        params = dict(self.config.get("params", {}))

        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        auth_env = self.config.get("auth_env")
        if auth_env:
            token = os.getenv(auth_env)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        if not self.robots.can_fetch(url):
            print(f"  [robots] blocked: {url}")
            return
        self.rl.wait(url)

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] {name}: {e}")
            return

        rows = _dig(payload, items_path)
        if not isinstance(rows, list):
            print(f"  [WARN] {name}: items_path did not resolve to a list")
            return

        for row in rows:
            identifier = str(_dig(row, field_map.get("identifier", "id")) or "")
            title = str(_dig(row, field_map.get("title", "title")) or "(untitled)")
            published = str(_dig(row, field_map.get("published", "")) or "")
            if since and published and published[:10] < since:
                continue
            yield Item(
                source=f"rest:{name}",
                identifier=identifier or title,
                title=title,
                url=str(_dig(row, field_map.get("url", "")) or ""),
                published=published,
                author=str(_dig(row, field_map.get("author", "")) or ""),
                content_md=str(_dig(row, field_map.get("content_md", "")) or ""),
            )

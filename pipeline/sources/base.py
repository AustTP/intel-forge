"""
base.py: the contract every source adapter implements.

A source is anything that yields Items: an RSS feed, a REST API, a sitemap, a
folder of files you drop in by hand, a database query. Adapters should be thin:
fetch, normalize into Item objects, yield. All the shared concerns
(rate limiting, robots, dedup, writing) live in core.py and are handled by the
ingest runner. An adapter never writes to the corpus itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional

from pipeline.core import Item, RateLimiter, RobotsCache


class Source(ABC):
    """Base class for all source adapters.

    Subclasses set a unique `key` (used as the Item.source prefix and as the
    name users list in config/sources.yaml) and implement `fetch()`.
    """

    #: Short, unique, filename-safe identifier, e.g. "rss:acme-blog".
    key: str = "source:unnamed"

    def __init__(self, rate_limiter: RateLimiter, robots: RobotsCache, config: dict):
        self.rl = rate_limiter
        self.robots = robots
        self.config = config or {}

    @abstractmethod
    def fetch(self, since: Optional[str] = None) -> Iterable[Item]:
        """Yield Items. `since` is an ISO date (YYYY-MM-DD) lower bound.

        Honor `since` where the upstream API supports date filtering; where it
        doesn't, yield everything and let the runner dedup. Yielding an item
        that's already in the corpus is fine; it will be skipped.
        """
        raise NotImplementedError

"""
Source registry.

Maps the `type` field in config/sources.yaml to an adapter class. To add your
own adapter: create a module in this package, subclass Source, and register it
in ADAPTERS below (or call register()).
"""

from pipeline.sources.base import Source
from pipeline.sources.rss import RSSSource
from pipeline.sources.rest_json import RestJSONSource
from pipeline.sources.sitemap import SitemapSource

# type name (as used in sources.yaml)  ->  adapter class
ADAPTERS: dict[str, type[Source]] = {
    "rss": RSSSource,
    "rest_json": RestJSONSource,
    "sitemap": SitemapSource,
}


def register(type_name: str, cls: type[Source]) -> None:
    ADAPTERS[type_name] = cls


def build(type_name: str, *args, **kwargs) -> Source:
    if type_name not in ADAPTERS:
        raise KeyError(
            f"Unknown source type {type_name!r}. "
            f"Known types: {', '.join(sorted(ADAPTERS))}"
        )
    return ADAPTERS[type_name](*args, **kwargs)

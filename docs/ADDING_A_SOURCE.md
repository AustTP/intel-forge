# Adding a source

A source adapter turns some external thing (feed, API, database, folder) into a
stream of `Item` objects. The runner handles the rest.

## Option A — use a shipped adapter

If your source is an RSS/Atom feed, a JSON list endpoint, or a site with a
sitemap, you don't write code at all — just add an entry to
`config/sources.yaml`. See `config/sources.example.yaml` for the shape of each.

## Option B — write a new adapter

For anything else, write a small class. Three steps.

**1. Create `pipeline/sources/mysource.py`:**

```python
from typing import Iterable, Optional
from pipeline.core import Item
from pipeline.sources.base import Source

class MySource(Source):
    key = "mysource"

    def fetch(self, since: Optional[str] = None) -> Iterable[Item]:
        name = self.config["name"]
        # ... fetch from wherever, honoring self.rl.wait(url) and
        #     self.robots.can_fetch(url) for anything you pull over HTTP ...
        for record in records:
            yield Item(
                source=f"mysource:{name}",
                identifier=record["stable_id"],   # must be stable across runs
                title=record["title"],
                url=record.get("url", ""),
                published=record.get("date", ""),  # ISO date if possible
                author=record.get("author", ""),
                content_md=record["body"],
            )
```

**2. Register it in `pipeline/sources/__init__.py`:**

```python
from pipeline.sources.mysource import MySource
ADAPTERS["mysource"] = MySource
```

**3. Reference it in `config/sources.yaml`:**

```yaml
  - name: my-instance
    type: mysource
    # ...any keys your adapter reads from self.config...
```

## Rules of thumb

- **Stable identifiers matter most.** `identifier` is what dedup keys off. Use
  the most permanent ID the source exposes (GUID, canonical URL, record ID). If
  it changes between runs, you'll get duplicates.
- **Be polite.** Call `self.rl.wait(url)` before HTTP requests and respect
  `self.robots.can_fetch(url)`. The shipped adapters show the pattern. For
  official APIs with documented rate limits, robots.txt may not apply — rate
  limit anyway.
- **Honor `since` when you can.** If the upstream supports date filtering, use
  it to pull only new items on scheduled runs. If not, yield everything; dedup
  makes it cheap.
- **Keep adapters thin.** No writing to the corpus, no global filtering — the
  runner does that. Just fetch, normalize, yield.

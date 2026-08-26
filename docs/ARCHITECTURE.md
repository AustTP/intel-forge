# Architecture

intel-forge is a template for a **self-updating intelligence system**: a
pipeline that continuously pulls raw material from sources you choose, keeps it
in a normalized corpus, and helps you distill that corpus into a library of
reusable, quality-gated *skills*. It is deliberately domain-agnostic: every
choice about *what* you're tracking lives in config and content, never in code.

```
   ┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
   │   SOURCES   │ ──▶ │    CORPUS    │ ──▶ │    SKILLS     │ ──▶ │  TRIAGE  │
   │ (adapters)  │     │ (normalized  │     │  (distilled,  │     │  (judge  │
   │ rss/api/... │     │   markdown)  │     │   reusable)   │     │  gate)   │
   └─────────────┘     └──────────────┘     └───────────────┘     └──────────┘
        ▲                     │                     ▲                   │
        │                     ▼                     │                   ▼
   sources.yaml          INDEX.md            SKILLS_INDEX.md      verdict + reasons
   relevance.yaml     (browsable)              (router)          (ACCEPT/REVISE/…)
```

## The five parts

**1. Sources → adapters.** Each source is declared in `config/sources.yaml` and
handled by an adapter in `pipeline/sources/`. The template ships three generic
adapters (`rss`, `rest_json`, `sitemap`); you add your own for anything else.
Adapters are thin: fetch, normalize into `Item` objects, yield. All shared
concerns (rate limiting, robots.txt, dedup, writing) live in `core.py`.

**2. Corpus.** Every ingested item becomes one normalized markdown file in
`corpus/`, with a metadata table (source, identifier, URL, dates) and the
content. Filenames embed a stable hash of `(source, identifier)`, so
re-ingesting updates in place instead of duplicating. The corpus is the raw
material; it is gitignored and never shared.

**3. Skills.** The refined output. A skill is a distilled, example-driven unit
of know-how synthesized from many corpus items: the thing you actually reuse.
Skills live in `skills/`, follow `_TEMPLATE.md`, and are routed via
`SKILLS_INDEX.md`. This library is the valuable product; the corpus and pipeline
are the means of producing it.

**4. Triage gate.** A rubric-driven LLM-as-judge (`pipeline/triage.py`) that
evaluates a *candidate* (a proposed skill, a synthesized finding, a draft)
against an explicit rubric (`config/triage_rubric.md`) and returns a structured,
auditable verdict with per-criterion reasoning. This is the strict quality bar.
What "good" means is entirely in your rubric; the machine is domain-neutral.

**5. Freshness / rot management.** Knowledge expires. `skill_freshness.py`
flags skills whose most recent review date is older than a threshold, so their
claims get re-checked against the current corpus instead of silently going
stale.

## Two gates, deliberately different

- The **relevance filter** (`is_relevant` in `core.py`, driven by
  `relevance.yaml`) runs at *ingest* time. It's a cheap keyword gate whose only
  job is to keep obvious junk out of the corpus. Keep it loose.
- The **triage gate** (`triage.py`, driven by `triage_rubric.md`) runs later,
  against candidates you're deciding whether to keep or promote. It's the strict
  one, and it explains itself.

Loose intake, strict promotion. Don't collapse them into one.

## What flows on a schedule

`scripts/refresh.sh` (see `scripts/schedule.md`) runs ingest → rebuild index →
freshness check on whatever cadence you set. Dedup makes an overlapping lookback
window safe. Triage is run on demand against candidates, not on every refresh.
Though you can wire it into the refresh or into CI if you want promotion gated
automatically.

## Extending it

- New source → `docs/ADDING_A_SOURCE.md`
- New skill → `docs/WRITING_A_SKILL.md`
- Tuning the judge → `docs/CONFIGURING_TRIAGE.md`
- Swap the keyword relevance filter for embeddings/an LLM classifier by
  replacing one function (`is_relevant`); the interface is stable.

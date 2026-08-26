# intel-forge

A template for building a **self-updating intelligence system** for any
domain. Point it at sources you care about; it keeps a normalized corpus
current, helps you distill that corpus into a library of reusable **skills**,
and gates their quality with a rubric-driven judge.

Nothing here is tied to a subject. What you track is entirely a matter of the
sources you configure and the skills you write. The repo ships **empty**: no
corpus, no sources, no skills, because the empty machine is the reusable part.

```
 SOURCES ──▶ CORPUS ──▶ SKILLS ──▶ TRIAGE GATE
 (adapters)  (markdown)  (distilled) (judge: ACCEPT / REVISE / REJECT / ESCALATE)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the pieces fit.

## Quickstart

```bash
# 1. Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (copy the examples, then edit for your domain)
cp config/sources.example.yaml       config/sources.yaml
cp config/relevance.example.yaml     config/relevance.yaml
cp config/triage.example.yaml        config/triage.yaml
cp config/triage_rubric.example.md   config/triage_rubric.md

# 3. Pull from your sources into the corpus
python3 -m pipeline.ingest --dry-run     # preview
python3 -m pipeline.ingest               # for real
python3 -m pipeline.build_index          # browsable corpus/INDEX.md

# 4. Write skills distilled from the corpus (see docs/WRITING_A_SKILL.md)
#    then gate them:
python3 -m pipeline.triage --input skills/your-skill.md

# 5. Keep it current on a schedule
bash scripts/refresh.sh                  # see scripts/schedule.md to automate
```

## What you configure

| File | Purpose |
|---|---|
| `config/sources.yaml` | where intelligence comes from (feeds, APIs, sitemaps, your own adapters) |
| `config/relevance.yaml` | cheap keyword gate that keeps obvious noise out of the corpus |
| `config/triage_rubric.md` | **the important one**: what "good" means for your domain |
| `config/triage.yaml` | triage verdicts + judge model settings |
| `skills/` | your distilled, reusable know-how (the valuable output) |

## Design in one line

**Loose intake, strict promotion, managed decay.** A cheap filter keeps junk out
of the corpus; a strict rubric-driven judge protects what becomes a skill; a
freshness check keeps skills from silently rotting.

## Extending

- Add a source → [`docs/ADDING_A_SOURCE.md`](docs/ADDING_A_SOURCE.md)
- Write a skill → [`docs/WRITING_A_SKILL.md`](docs/WRITING_A_SKILL.md)
- Tune the judge → [`docs/CONFIGURING_TRIAGE.md`](docs/CONFIGURING_TRIAGE.md)
- Schedule refreshes → [`scripts/schedule.md`](scripts/schedule.md)

## A note on what to share

The corpus (other people's raw material) and your accumulated skills are *not*
in this template on purpose, and `.gitignore` keeps your corpus out of git. The
skills you build are your refined product; the corpus and running pipeline are
your means of producing it. Share the template freely; be deliberate about
sharing what you accumulate on top of it.

## Requirements

Python 3.10+. Core deps in `requirements.txt` (`requests`, `feedparser`,
`PyYAML`, `html2text`). The reference triage judge additionally needs
`anthropic` and an `ANTHROPIC_API_KEY`, but any model provider can be plugged in.

## License

MIT. See [`LICENSE`](LICENSE).

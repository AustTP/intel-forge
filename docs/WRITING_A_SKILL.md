# Writing a skill

A skill is the **refined output** of your intelligence system: a distilled,
reusable unit of know-how synthesized from the corpus. Corpus items are inputs;
skills are what you make from them. The skill library is the valuable product —
treat it as such.

## The loop

1. **Accumulate.** Let the pipeline fill `corpus/` from your sources.
2. **Notice a pattern.** Several corpus items point at the same recurring
   technique, failure mode, rule, or method.
3. **Distill.** Write it up as a skill (`skills/<name>.md`, from `_TEMPLATE.md`):
   purpose, when to use, method, at least one worked example, the sources it
   came from, and known limitations.
4. **Gate it.** Run it through the triage gate before you trust it:
   ```bash
   python3 -m pipeline.triage --input skills/<name>.md
   ```
   Fix what the judge flags. Only `ACCEPT` earns a place in the library.
5. **Route it.** Add a row to `SKILLS_INDEX.md` so it's discoverable.
6. **Keep it fresh.** Update the `Last reviewed:` date whenever you re-validate.
   `skill_freshness.py` uses it to tell you when a skill is overdue.

## What makes a good skill

- **Concrete over abstract.** A worked example transfers where a general
  description doesn't. If you can only describe it vaguely, it isn't ready.
- **Traceable.** Cite the corpus items it's distilled from, so claims can be
  re-checked when those sources change.
- **Honest about limits.** Say where it breaks and what it assumes. A library
  you can trust is worth more than a large one.
- **Self-contained.** A competent practitioner should be able to act on it
  without hunting for missing context.

## Why skills, not just the corpus

The corpus is bulky, noisy, and mostly other people's raw material. The skills
are compact, validated, and yours. When you need to *demonstrate* what your
system produces without handing over the whole engine, the skills are what you
show: they prove the capability and the results while the corpus and pipeline —
the means of production — stay with you.

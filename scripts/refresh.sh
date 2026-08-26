#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# refresh.sh — keep the corpus current and flag stale skills.
#
# Pulls a recent window from every configured source, rebuilds the index, and
# reports which skills are overdue for re-verification. Safe to run repeatedly:
# dedup means an overlapping lookback window creates no duplicates.
#
# Run manually:            bash scripts/refresh.sh
# Schedule it:             see scripts/schedule.md (cron / systemd / launchd)
# ---------------------------------------------------------------------------
set -uo pipefail

# Resolve repo root regardless of where this is called from.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Optional: load secrets (API tokens) from an untracked env file.
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a

# Pick a python. Override with PYTHON=/path/to/python bash scripts/refresh.sh
PY="${PYTHON:-python3}"

LOGDIR="$ROOT/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/refresh_$(date +%Y%m%d_%H%M%S).log"

# Lookback window (days). Overlap is safe; dedup drops anything already stored.
LOOKBACK="${LOOKBACK:-10}"
SINCE="$("$PY" -c "import datetime;print((datetime.date.today()-datetime.timedelta(days=$LOOKBACK)).isoformat())")"

{
  echo "======================================================================"
  echo "Corpus refresh — $(date)  (pulling since $SINCE)"
  echo "======================================================================"

  echo ""; echo "### [1/3] Ingest new items from all sources ###"
  "$PY" -m pipeline.ingest --since "$SINCE"

  echo ""; echo "### [2/3] Rebuild corpus index ###"
  "$PY" -m pipeline.build_index

  echo ""; echo "### [3/3] Skill freshness check ###"
  "$PY" -m pipeline.skill_freshness --threshold "${FRESHNESS_DAYS:-180}"

  echo ""; echo "Refresh complete — $(date)"
} 2>&1 | tee "$LOG"

# Keep only the 12 most recent logs.
ls -1t "$LOGDIR"/refresh_*.log 2>/dev/null | tail -n +13 | xargs rm -f 2>/dev/null || true

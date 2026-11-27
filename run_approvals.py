"""Every ~15 minutes: housekeeping. Posts that kept failing to publish are dropped after
PENDING_HOURS, and draft folders older than a few days are deleted to keep the repo small.
(Posting itself is fully automatic; nothing here needs a human.)
"""
from __future__ import annotations

import datetime as dt
import os
import shutil
import sys
import traceback

import state

PENDING_HOURS = int(os.getenv("PENDING_HOURS") or "6")
KEEP_DRAFT_DAYS = 3


def main() -> None:
    st = state.load()
    now = state.now_ist()
    stale = [d for d, e in st["pending"].items()
             if now - dt.datetime.fromisoformat(e["created"]) > dt.timedelta(hours=PENDING_HOURS)]
    for d in stale:
        del st["pending"][d]
    if stale:
        print("Dropped stale drafts:", stale)

    if os.path.isdir(state.DRAFTS_DIR):
        cutoff = (now - dt.timedelta(days=KEEP_DRAFT_DAYS)).strftime("%Y%m%d")
        for name in os.listdir(state.DRAFTS_DIR):
            if name not in st["pending"] and name[:8] < cutoff:
                shutil.rmtree(os.path.join(state.DRAFTS_DIR, name), ignore_errors=True)
    state.save(st)
    print("Housekeeping done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)

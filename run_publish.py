"""Hourly job, step 2 of 2: post every "ready" draft to Instagram (+ LinkedIn for top stories).

Runs after the workflow has pushed the new images, because Instagram downloads them
from the repo's public link.
"""
from __future__ import annotations

import sys
import time
import traceback

import state
from publisher import notify, publish_entry

MAX_ATTEMPTS = 3


def main() -> None:
    st = state.load()
    ready = [(d, e) for d, e in sorted(st["pending"].items()) if e.get("status") == "ready"]
    if not ready:
        print("Nothing ready to post.")
        return
    time.sleep(20)  # give GitHub's public file links a moment to serve the just-pushed images

    for draft_id, entry in ready:
        entry["attempts"] = entry.get("attempts", 0) + 1
        finished, report = publish_entry(st, draft_id, entry)
        state.save(st)
        if finished:
            notify(f"✅ Posted: {entry['title']}\n" + "\n".join(report))
        elif entry["attempts"] >= MAX_ATTEMPTS:
            entry["status"] = "failed"
            notify(f"❌ Gave up after {MAX_ATTEMPTS} tries: {entry['title']}\n" + "\n".join(report))
        else:
            print(f"Will retry {draft_id} next run:", report)
    state.save(st)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        traceback.print_exc()
        notify(f"⚠️ vGudia publish run failed: {type(exc).__name__}: {exc}"[:600])
        sys.exit(1)

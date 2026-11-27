"""Hourly job, step 1 of 2: fetch news -> AI writes the Bengali post -> fact check ->
poster(s) made from the vGudia template + a free photo. Passing drafts are marked "ready";
run_publish.py posts them after the images are pushed to the public repo.

    python run_hourly.py              # normal run (needs GEMINI_API_KEY; PEXELS_API_KEY for photos)
    python run_hourly.py --no-images  # only writing + fact check (to check the writing)
"""
from __future__ import annotations

import glob
import json
import os
import sys
import traceback

import state
from checker import check_facts
from news import fetch_new_stories
from poster import render_post
from publisher import notify
from writer import write_post


def _write(folder: str, name: str, content) -> None:
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        if isinstance(content, str):
            f.write(content)
        else:
            json.dump(content, f, ensure_ascii=False, indent=1)


def main() -> None:
    no_images = "--no-images" in sys.argv
    st = state.load()

    stories = fetch_new_stories(set(st["seen"]))
    if not stories:
        print("No new stories this hour.")
        return
    print(f"{len(stories)} new stories:")
    for s in stories:
        print(f"  [{s.source}] {s.headline}")

    recent = [p["headline"] for p in st["posted"]] + [p["headline"] for p in st["pending"].values()]
    plan = write_post(stories, recent)
    st["seen"].extend(s.url for s in stories)
    state.save(st)
    if plan["decision"] == "skip":
        print(f"Skipped: {plan['reason']}")
        return

    # Fact check, with one rewrite if it fails.
    story = stories[plan["story_index"]]
    facts_ok, problems = check_facts(plan, story)
    if not facts_ok:
        print("Fact check failed, rewriting:", problems)
        plan = write_post([story], recent, feedback=problems)
        if plan["decision"] == "skip":
            print("Skipped after rewrite.")
            return
        facts_ok, problems = check_facts(plan, story)
    if not facts_ok:
        notify(f"⏭️ Not posted (failed the fact check twice): {story.headline}\n- " + "\n- ".join(problems))
        return

    now = state.now_ist()
    draft_id = now.strftime("%Y%m%d-%H%M")
    folder = os.path.join(state.DRAFTS_DIR, draft_id)
    os.makedirs(folder, exist_ok=True)
    _write(folder, "plan.json", plan)
    _write(folder, "caption.txt", plan["caption"])
    _write(folder, "linkedin.txt", plan["linkedin_text"])
    print(f"Chosen ({plan['format']}, importance {plan['importance']}): {story.headline}")
    if no_images:
        print(f"--no-images: draft text written to drafts/{draft_id}/")
        return

    used = set(st.setdefault("used_photos", []))
    paths = render_post(plan, now.date(), folder, used)
    st["used_photos"] = sorted(used)[-500:]
    # Keep only the finished posters in the repo (photos and HTML were just ingredients).
    for leftover in glob.glob(os.path.join(folder, "photo-*")) + glob.glob(os.path.join(folder, "slide-*.html")):
        os.remove(leftover)

    st["pending"][draft_id] = {
        "created": now.isoformat(),
        "headline": story.headline,
        "title": plan["telegram_title"],
        "importance": plan["importance"],
        "images": [f"drafts/{draft_id}/{os.path.basename(p)}" for p in paths],
        "status": "ready",
    }
    state.save(st)
    print(f"Made {len(paths)} image(s); run_publish.py will post them.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        traceback.print_exc()
        notify(f"⚠️ vGudia hourly run failed: {type(exc).__name__}: {exc}"[:600])
        sys.exit(1)

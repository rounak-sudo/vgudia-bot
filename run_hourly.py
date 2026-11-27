"""Hourly job, step 1 of 2: fetch news -> Claude writes the post -> fact check ->
OpenAI draws the poster(s) -> poster check. Passing drafts are marked "ready";
run_publish.py posts them after the images are pushed to the public repo.
Drafts that fail a check are sent to Telegram for a manual decision (or simply expire).

    python run_hourly.py              # normal run (needs the keys)
    python run_hourly.py --no-images  # only Claude writing + fact check (to check the writing)
"""
from __future__ import annotations

import json
import os
import sys
import traceback

import state
from checker import check_facts, check_image
from news import fetch_new_stories
from poster import all_prompts, expected_text, generate_image
from publisher import notify
from writer import write_post

IMAGE_TRIES = 3   # draw each poster up to 3 times until it passes the text check


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

    # 1) Fact check, with one rewrite if it fails.
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
    prompts = all_prompts(plan, now.date())
    _write(folder, "plan.json", plan)
    _write(folder, "prompts.json", prompts)
    _write(folder, "caption.txt", plan["caption"])
    _write(folder, "linkedin.txt", plan["linkedin_text"])
    print(f"Chosen ({plan['format']}, importance {plan['importance']}): {story.headline}")
    if no_images:
        print(f"--no-images: draft text written to drafts/{draft_id}/")
        return

    # 2) Draw each image and check its text; redraw on failure.
    images, image_problems = [], []
    for i, prompt in enumerate(prompts):
        rel = f"drafts/{draft_id}/v1-{i + 1}.jpg"
        path = os.path.join(state.ROOT, rel)
        for attempt in range(1, IMAGE_TRIES + 1):
            generate_image(prompt, path)
            ok, issues = check_image(path, expected_text(plan, i, now.date()))
            print(f"  image {i + 1} attempt {attempt}: {'OK' if ok else issues}")
            if ok:
                break
        else:
            image_problems += [f"slide {i + 1}: {p}" for p in issues]
        images.append(rel)
        if image_problems and len(prompts) > 1:
            # A carousel with a broken slide can't go out; stop here instead of paying for more images.
            notify(f"⏭️ Not posted (carousel slide {i + 1} failed the poster check {IMAGE_TRIES} times): "
                   f"{story.headline}\n- " + "\n- ".join(image_problems[:5]))
            return

    entry = {
        "created": now.isoformat(),
        "headline": story.headline,
        "title": plan["telegram_title"],
        "importance": plan["importance"],
        "images": images,
        "version": 1,
        "status": "ready" if not image_problems else "review",
        "problems": image_problems,
        "message_id": None,
    }
    st["pending"][draft_id] = entry
    state.save(st)

    if entry["status"] == "ready":
        print("Passed all checks: will be posted by run_publish.py")
    else:
        print("Poster check failed; sending to Telegram for review.")
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            import telegram_bot
            entry["message_id"] = telegram_bot.send_draft(
                draft_id, [os.path.join(state.ROOT, p) for p in images],
                "🟡 Needs your OK (poster check failed):\n" + "\n".join(f"- {p}" for p in image_problems[:6]),
                plan["caption"])
            state.save(st)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        traceback.print_exc()
        notify(f"⚠️ vGudia hourly run failed: {type(exc).__name__}: {exc}"[:600])
        sys.exit(1)

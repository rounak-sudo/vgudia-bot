"""Build vGudia poster / carousel prompts and generate the images with OpenAI's image model."""
from __future__ import annotations

import base64
import datetime as dt
import os

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই",
             "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]

ICON_WORDS = {
    "chart-up": "rising bar-chart icon", "chart-down": "falling chart icon",
    "bank": "bank-building icon", "globe": "globe icon", "handshake": "handshake icon",
    "target": "target icon", "coins": "stack-of-coins icon", "oil": "oil-barrel icon",
    "factory": "factory icon", "ship": "cargo-ship icon", "warning": "warning icon",
    "document": "document icon",
}

NOTICE = "শুধুমাত্র তথ্যের জন্য, বিনিয়োগ পরামর্শ নয়"
SWIPE = "সোয়াইপ করুন →"
COMMENT_CTA = "আপনার মত কমেন্টে জানান"

STYLE = ("Create a 1:1 square Instagram {what} in a premium Indian financial-media style. "
         "Colour palette: deep navy blue and saffron orange, with white cards and a yellow notice bar. "
         "Bright, sharp, professional, high detail.")

FOOTER = ('FOOTER: a dark navy band with a thin saffron line on top, containing: "vGudia" (bold, the "v" in '
          'saffron, rest white) | "Making Market Simple" (white italic) | "বাজারকে সহজ করা" (yellow bold)')

RULES = """STRICT RULES:
- Write every piece of text EXACTLY as given above, letter for letter. Bengali spelling must be perfect.
- Do NOT add any other text, numbers, prices, index levels, tickers or percentages anywhere in the image, including on screens or boards in the background.
- Do NOT draw any company logos, emblems or trademarks. Company names appear only as plain text where given.
- Keep all text inside the square with comfortable margins."""


def bn_num(n: int) -> str:
    return str(n).translate(BN_DIGITS)


def bengali_date(day: dt.date) -> str:
    return f"{bn_num(day.day)} {BN_MONTHS[day.month - 1]} {bn_num(day.year)}"


def _tag(plan: dict, day: dt.date) -> str:
    return f'{plan["category_tag"]} | {bengali_date(day)}'


def cover_prompt(plan: dict, day: dt.date, total: int = 1) -> str:
    accent = plan.get("headline_accent", "")
    accent_line = (
        f' The words "{accent}" are in saffron orange, the rest in dark navy.'
        if accent and accent in plan["headline"] else ""
    )

    if len(plan.get("data_items", [])) >= 2:
        items = "; ".join(
            f'"{d["label"]}" = "{d["value"]}"' + (" (highlighted in saffron)" if d["highlight"] else "")
            for d in plan["data_items"]
        )
        data_block = (
            f'\nKEY FIGURES STRIP: a clean white rounded strip with a navy pill title "{plan["data_title"]}", '
            f"showing these items side by side, each label above its value in a grey pill: {items}. "
            "Company and index names are plain text only, no logos.\n"
        )
    else:
        data_block = ""

    cards = "\n".join(
        f'Card {i}: {"red" if c["color"] == "red" else "navy blue"} header with a white {ICON_WORDS.get(c["icon"], "simple icon")} '
        f'and the header text "{c["header"]}"; body text "{c["body"]}"'
        for i, c in enumerate(plan["cards"], 1)
    )

    carousel = (
        f'\nCAROUSEL MARKERS: a small saffron rounded badge in the top-right corner with the text "{bn_num(1)}/{bn_num(total)}", '
        f'and a saffron pill just above the footer on the right with white text "{SWIPE}".\n'
        if total > 1 else ""
    )

    return f"""{STYLE.format(what="news poster" if total == 1 else "carousel cover slide")}

TOP-LEFT TAG: a navy pill with a saffron left edge, white bold italic text: "{_tag(plan, day)}"

MAIN HEADLINE: very large, extra-bold Bengali text, left side, up to 3 lines: "{plan["headline"]}".{accent_line}

BANNER: an orange brush-stroke banner under the headline with white bold Bengali text: "{plan["banner"]}"

BACKGROUND / RIGHT SIDE VISUAL (photorealistic): {plan["scene"]} Light blue sky, soft daylight.
{data_block}
THREE INFO CARDS in a row (rounded white cards with coloured headers and an orange bottom edge):
{cards}

YELLOW NOTICE BAR with a warning-triangle icon: "{NOTICE}"
{carousel}
{FOOTER}

{RULES}"""


def slide_prompt(plan: dict, slide: dict, number: int, total: int, day: dt.date) -> str:
    points = "\n".join(f'{i}. "{p}"' for i, p in enumerate(slide["points"], 1))
    last = number == total
    ending = (
        f'YELLOW NOTICE BAR with a warning-triangle icon: "{NOTICE}"\n'
        f'Above it, a navy pill with white bold text: "{COMMENT_CTA}"'
        if last else
        f'A saffron pill just above the footer on the right with white text: "{SWIPE}"'
    )
    return f"""{STYLE.format(what=f"carousel slide (slide {number} of {total})")} It must look like part of the same series as the cover: same colours, fonts and footer.

TOP-LEFT TAG: a navy pill with a saffron left edge, white bold italic text: "{_tag(plan, day)}"
TOP-RIGHT: a small saffron rounded badge with the text "{bn_num(number)}/{bn_num(total)}"

SLIDE TITLE: large, extra-bold dark navy Bengali text with a short saffron brush-stroke underline: "{slide["title"]}"

MAIN CONTENT: a large white rounded card covering most of the slide, with these Bengali points, each starting with a saffron round bullet, in clear bold text with generous spacing:
{points}

VISUAL (photorealistic, in the background behind / beside the card, not covering any text): {slide["scene"]}

{ending}

{FOOTER}

{RULES}"""


def all_prompts(plan: dict, day: dt.date) -> list[str]:
    """Cover first, then one prompt per detail slide (empty slides list = single poster)."""
    slides = plan.get("slides") or []
    total = 1 + len(slides)
    prompts = [cover_prompt(plan, day, total)]
    for n, slide in enumerate(slides, 2):
        prompts.append(slide_prompt(plan, slide, n, total, day))
    return prompts


def expected_text(plan: dict, index: int, day: dt.date) -> list[str]:
    """The exact texts that must appear on image `index` (0 = cover). Used by the poster check."""
    slides = plan.get("slides") or []
    total = 1 + len(slides)
    texts = [_tag(plan, day), "vGudia", "Making Market Simple", "বাজারকে সহজ করা"]
    if index == 0:
        texts += [plan["headline"], plan["banner"], NOTICE]
        texts += [t for c in plan["cards"] for t in (c["header"], c["body"])]
        if len(plan.get("data_items", [])) >= 2:
            texts += [plan["data_title"]] + [t for d in plan["data_items"] for t in (d["label"], d["value"])]
        if total > 1:
            texts += [f"{bn_num(1)}/{bn_num(total)}", SWIPE]
    else:
        slide = slides[index - 1]
        texts += [slide["title"], *slide["points"], f"{bn_num(index + 1)}/{bn_num(total)}"]
        texts += [NOTICE, COMMENT_CTA] if index + 1 == total else [SWIPE]
    return texts


def generate_image(prompt: str, out_path: str) -> None:
    """Generate one poster as a JPEG at out_path using the OpenAI Images API."""
    from openai import OpenAI  # imported here so the rest of the app runs without it

    client = OpenAI()
    result = client.images.generate(
        model=os.getenv("OPENAI_IMAGE_MODEL") or "gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality=os.getenv("OPENAI_IMAGE_QUALITY") or "high",
        output_format="jpeg",
        output_compression=90,
        n=1,
    )
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(result.data[0].b64_json))

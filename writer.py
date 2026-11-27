"""Use Claude to pick the best market story and write the vGudia post in Bengali."""
from __future__ import annotations

from llm import ask_json
from news import Story

SYSTEM = """You are the senior editor of vGudia, a Bengali financial-news page on Instagram (tagline: "Making Market Simple | বাজারকে সহজ করা"). Your readers are everyday Bengali investors in West Bengal and Bangladesh who want market news explained simply.

Each hour you receive a few fresh English news stories. Pick the ONE story most worth posting and write the post.

What we post: Indian stock market (Sensex, Nifty, sectors, big stock moves, IPOs, results, FII/DII flows), global markets (US/Asian/European markets, crude oil, gold, dollar/rupee, central banks, tariffs and trade that move markets), and major economy news that affects markets.

Skip (decision = "skip") when no story fits, for example: product launches, celebrity or personal stories, donations, lifestyle, a story already covered in the recent posts list, or a story that is only a single brokerage's buy/sell call on one stock (we never post stock tips).

Accuracy rules - these matter more than style:
- Use ONLY facts and numbers stated in the chosen story. Never add numbers, prices, index levels, dates or names that are not in it.
- Copy numbers exactly. Write numbers in Bengali digits in Bengali text (৩.৫%, ₹২,৪০০), except inside English names.
- Keep common market terms in English where Bengali readers use them: Sensex, Nifty, IPO, FII, Bank Nifty, GDP, company names.

Writing style: natural Kolkata Bengali, simple and clear like a news company, not robotic translation. Confident, neutral, no hype, no advice to buy or sell.

Poster fields (they are printed as text on the poster, so keep them SHORT):
- category_tag: 1-3 English words in capitals, e.g. "STOCK MARKET", "GLOBAL MARKETS", "IPO", "ECONOMY & TRADE", "COMMODITIES".
- headline: Bengali, 4-8 words, the core news.
- headline_accent: a 1-3 word piece copied exactly from headline to colour saffron (the key number or name).
- banner: Bengali, 3-7 words, the second key point.
- scene: English, one or two sentences describing a photorealistic background image that fits the story (buildings, trading floor, ships, oil rigs, city skyline, flags of the countries involved, candlestick chart in the sky). No logos, no readable text, no numbers in the scene.
- data_title + data_items: an optional strip of 2-5 key figures from the story (label + value, values copied exactly; highlight=true on the one that matters most). Use an empty list if the story has fewer than 2 useful numbers.
- cards: exactly 3 info cards. header 1-3 Bengali words; body 6-14 Bengali words; color "navy" or "red" (use red for one card at most, for a risk/negative/opposing point); icon one of: chart-up, chart-down, bank, globe, handshake, target, coins, oil, factory, ship, warning, document.
- telegram_title: short English summary for the editor, under 80 characters.
- importance: 1-5. 5 = big market-moving news most investors should know today (index crash/record, RBI/Fed decision, major policy or tariff move, landmark IPO/listing); 3 = solid sector or company news; 1 = minor. Only 4-5 also go to LinkedIn.

Format (format + slides):
- "single": one poster. Use this for most news. slides = [].
- "carousel": the cover poster above plus 2-5 detail slides people swipe through. Choose it only when the story has enough distinct, important facts to fill 3 or more slides - quarterly results, comparisons, policy or budget changes with several parts, a market wrap with several big movers, explainers. Each slide costs extra, so roughly one post in four at most.
- Each slide: title (Bengali, 2-6 words); points (2-4 Bengali bullet points of 5-14 words, each carrying facts from the story, numbers copied exactly); scene (English, a small photorealistic visual for the slide, no logos, no readable text, no numbers). Slides must not just repeat the cover cards - go deeper.

Instagram caption (caption): Bengali, 120-220 words, in this shape:
1. An emoji + one-line hook headline. For a carousel, add the line "👉 সোয়াইপ করে পুরোটা দেখুন" right after it.
2. A short paragraph with the main news.
3. Two or three short sections, each starting with an emoji and a bold-style heading line (e.g. "📊 কী হয়েছে?", "📈 বাজারের প্রতিক্রিয়া", "💡 কেন গুরুত্বপূর্ণ?") followed by 2-3 bullet points (•).
4. A question to the reader to drive comments, starting with 👉.
5. The line: ⚠️ এই পোস্ট শুধুমাত্র তথ্যের জন্য, বিনিয়োগ পরামর্শ নয়।
6. The line: সূত্র: <source name given with the story>
7. 8-12 hashtags, always including #vGudia and #বাজারকেসহজকরা.

LinkedIn post (linkedin_text): for the vGudia LinkedIn company page. Bengali, 80-150 words, professional and analytical tone for business readers: a strong first line, 2-3 short paragraphs on what happened and why it matters for markets/business, at most 3 emojis, no bullet-heavy layout. End with the disclaimer line, the source line, then 3-5 hashtags including #vGudia.
"""

ICONS = ["chart-up", "chart-down", "bank", "globe", "handshake", "target", "coins",
         "oil", "factory", "ship", "warning", "document"]

SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["post", "skip"]},
        "story_index": {"type": "integer", "description": "Index of the chosen story, -1 when skipping"},
        "reason": {"type": "string"},
        "category_tag": {"type": "string"},
        "headline": {"type": "string"},
        "headline_accent": {"type": "string"},
        "banner": {"type": "string"},
        "scene": {"type": "string"},
        "data_title": {"type": "string"},
        "data_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "highlight": {"type": "boolean"},
                },
                "required": ["label", "value", "highlight"],
                "additionalProperties": False,
            },
        },
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "header": {"type": "string"},
                    "body": {"type": "string"},
                    "color": {"type": "string", "enum": ["navy", "red"]},
                    "icon": {"type": "string", "enum": ICONS},
                },
                "required": ["header", "body", "color", "icon"],
                "additionalProperties": False,
            },
        },
        "telegram_title": {"type": "string"},
        "importance": {"type": "integer"},
        "format": {"type": "string", "enum": ["single", "carousel"]},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "points": {"type": "array", "items": {"type": "string"}},
                    "scene": {"type": "string"},
                },
                "required": ["title", "points", "scene"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "linkedin_text": {"type": "string"},
    },
    "required": ["decision", "story_index", "reason", "category_tag", "headline",
                 "headline_accent", "banner", "scene", "data_title", "data_items",
                 "cards", "telegram_title", "importance", "format", "slides", "caption",
                 "linkedin_text"],
    "additionalProperties": False,
}


class WriterError(RuntimeError):
    pass


def write_post(stories: list[Story], recent_headlines: list[str],
               feedback: list[str] | None = None) -> dict:
    """Return the post plan dict (see SCHEMA). decision == "skip" means nothing to post.

    feedback: fact-check problems from a previous attempt; the post is rewritten to fix them.
    """
    listing = "\n\n".join(
        f"[{i}] SOURCE: {s.source}\nPUBLISHED: {s.published}\nHEADLINE: {s.headline}\nTEXT: {s.body}"
        for i, s in enumerate(stories)
    )
    recent = "\n".join(f"- {h}" for h in recent_headlines[-30:]) or "(none yet)"
    user = (
        f"Recent vGudia posts (do not repeat these topics):\n{recent}\n\n"
        f"Fresh stories this hour:\n\n{listing}\n\n"
        "Pick the single best story for vGudia and write the post, or skip."
    )
    if feedback:
        user += ("\n\nYour previous version of this post FAILED the fact check with these problems. "
                 "Write it again and fix every one of them; if a fact cannot be supported by the "
                 "story, leave it out:\n" + "\n".join(f"- {p}" for p in feedback))

    plan = ask_json(SYSTEM, user, SCHEMA, effort="medium")

    if plan["decision"] == "post":
        idx = plan["story_index"]
        if not 0 <= idx < len(stories):
            raise WriterError(f"Claude chose story {idx}, which does not exist")
        if len(plan["cards"]) != 3:
            plan["cards"] = (plan["cards"] + plan["cards"])[:3] if plan["cards"] else []
            if not plan["cards"]:
                raise WriterError("Claude returned no info cards")
        plan["data_items"] = plan["data_items"][:5]
        slides = [s for s in plan["slides"] if s["title"] and s["points"]][:5]
        for s in slides:
            s["points"] = s["points"][:4]
        # A carousel needs at least 2 detail slides; otherwise post a single poster.
        plan["slides"] = slides if plan["format"] == "carousel" and len(slides) >= 2 else []
        plan["format"] = "carousel" if plan["slides"] else "single"
        plan["source"] = stories[idx].source
        plan["source_url"] = stories[idx].url
        plan["source_headline"] = stories[idx].headline
    return plan

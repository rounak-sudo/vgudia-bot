"""Fetch fresh stock-market / global-market stories from Moneycontrol and Inshorts.

Both sites embed a schema.org NewsArticle JSON-LD block on each story page,
which carries the headline, full text and publish time. We read that.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field

import requests

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
}

MONEYCONTROL_LISTS = [
    "https://www.moneycontrol.com/news/business/markets/",
    "https://www.moneycontrol.com/news/business/economy/",
]
INSHORTS_LISTS = [
    "https://inshorts.com/en/read/business",
]

# Moneycontrol article URLs look like .../markets/<slug>-14089420.html
MC_LINK = re.compile(
    r'href="(https://www\.moneycontrol\.com/news/business/(?:markets|economy)/[a-z0-9\-]+-\d+\.html)"'
)
LD_BLOCK = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


@dataclass
class Story:
    url: str
    source: str
    headline: str
    body: str
    published: str = ""
    extra: dict = field(default_factory=dict)


def _get(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=25)
    r.raise_for_status()
    return r.text


def _clean(text: str) -> str:
    # Moneycontrol double-escapes entities (&amp;#039;), so unescape twice.
    text = html.unescape(html.unescape(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _json_ld_objects(page: str):
    for raw in LD_BLOCK.findall(page):
        try:
            data = json.loads(raw.strip(), strict=False)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                yield item


def _read_article(url: str, source: str) -> Story | None:
    try:
        page = _get(url)
    except requests.RequestException:
        return None
    for obj in _json_ld_objects(page):
        if obj.get("@type") in ("NewsArticle", "Article") and obj.get("articleBody"):
            headline = _clean(obj.get("headline", ""))
            headline = re.sub(r"\s*\|\s*Inshorts$", "", headline)
            return Story(
                url=url,
                source=source,
                headline=headline,
                body=_clean(obj["articleBody"])[:4000],
                published=obj.get("datePublished", ""),
            )
    return None


def moneycontrol_links() -> list[str]:
    links: list[str] = []
    for list_url in MONEYCONTROL_LISTS:
        try:
            page = _get(list_url)
        except requests.RequestException:
            continue
        for link in MC_LINK.findall(page):
            if "liveblog" in link or "live-updates" in link:
                continue  # live blogs are long running pages, not single stories
            if link not in links:
                links.append(link)
    return links


def inshorts_links() -> list[str]:
    links: list[str] = []
    for list_url in INSHORTS_LISTS:
        try:
            page = _get(list_url)
        except requests.RequestException:
            continue
        for obj in _json_ld_objects(page):
            if obj.get("@type") == "ItemList":
                for el in obj.get("itemListElement", []):
                    url = el.get("url")
                    if url and url not in links:
                        links.append(url)
    return links


def fetch_new_stories(seen: set[str], limit: int = 12) -> list[Story]:
    """Return up to `limit` stories whose URL is not in `seen`, newest first per site."""
    mc = [u for u in moneycontrol_links() if u not in seen]
    ins = [u for u in inshorts_links() if u not in seen]

    # Interleave the two sources so neither crowds the other out.
    ordered: list[tuple[str, str]] = []
    for i in range(max(len(mc), len(ins))):
        if i < len(mc):
            ordered.append((mc[i], "Moneycontrol"))
        if i < len(ins):
            ordered.append((ins[i], "Inshorts"))

    stories: list[Story] = []
    for url, source in ordered:
        if len(stories) >= limit:
            break
        story = _read_article(url, source)
        if story:
            stories.append(story)
    return stories


if __name__ == "__main__":
    for s in fetch_new_stories(set(), limit=6):
        print(f"[{s.source}] {s.headline}\n  {s.url}\n  {s.body[:160]}...\n")

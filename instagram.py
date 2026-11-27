"""Publish a single image post through Instagram's official content-publishing API."""
from __future__ import annotations

import os
import time

import requests

HOST = os.getenv("IG_GRAPH_HOST") or "graph.instagram.com"
VERSION = os.getenv("IG_GRAPH_VERSION") or "v23.0"


class InstagramError(RuntimeError):
    pass


def _call(method: str, path: str, **fields) -> dict:
    fields["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    url = f"https://{HOST}/{VERSION}/{path}"
    if method == "GET":
        r = requests.get(url, params=fields, timeout=60)
    else:
        r = requests.post(url, data=fields, timeout=60)
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or "error" in body:
        # Report only Instagram's message: the request URL can contain the access token.
        err = body.get("error", {})
        raise InstagramError(f"Instagram {path.split('/')[-1]} failed ({r.status_code}): "
                             f"{err.get('message', 'unknown error')}")
    return body


def _wait_ready(container: str) -> None:
    for _ in range(30):  # Instagram downloads and checks the image(s) first
        status = _call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Instagram could not process the image (status {status})")
        time.sleep(4)
    raise InstagramError("Instagram took too long to process the image")


def publish(image_urls: list[str], caption: str) -> str:
    """Post one image, or a carousel when given 2+ public JPEG URLs. Returns the permalink (or id)."""
    user = os.environ["IG_USER_ID"]
    if len(image_urls) == 1:
        container = _call("POST", f"{user}/media", image_url=image_urls[0], caption=caption)["id"]
    else:
        children = []
        for url in image_urls[:10]:
            child = _call("POST", f"{user}/media", image_url=url, is_carousel_item="true")["id"]
            _wait_ready(child)
            children.append(child)
        container = _call("POST", f"{user}/media", media_type="CAROUSEL",
                          children=",".join(children), caption=caption)["id"]
    _wait_ready(container)

    media_id = _call("POST", f"{user}/media_publish", creation_id=container)["id"]
    try:
        return _call("GET", media_id, fields="permalink").get("permalink", media_id)
    except InstagramError:
        return media_id

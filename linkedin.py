"""Post to the vGudia LinkedIn Company Page through LinkedIn's official Posts API.

Needs a token with the w_organization_social permission (Community Management API).
"""
from __future__ import annotations

import os
import re

import requests

API = "https://api.linkedin.com/rest"
# LinkedIn versions its API by month (YYYYMM) and retires old months after about a year.
VERSION = os.getenv("LINKEDIN_VERSION") or "202609"

# LinkedIn's "little text" format treats these characters as markup unless escaped.
_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")
_HASHTAG = re.compile(r"\\#([^\s\\#]+)")


class LinkedInError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(os.getenv("LINKEDIN_ACCESS_TOKEN") and os.getenv("LINKEDIN_ORG_ID"))


def _headers(json_body: bool = True) -> dict:
    h = {
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "LinkedIn-Version": VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _fail(what: str, r: requests.Response) -> LinkedInError:
    try:
        msg = r.json().get("message", r.text[:200])
    except ValueError:
        msg = r.text[:200]
    return LinkedInError(f"LinkedIn {what} failed ({r.status_code}): {msg}")


def format_commentary(text: str) -> str:
    """Escape reserved characters, then turn #words back into real LinkedIn hashtags."""
    escaped = _RESERVED.sub(r"\\\1", text)
    return _HASHTAG.sub(lambda m: "{hashtag|\\#|" + m.group(1) + "}", escaped)


def _upload(path: str, owner: str) -> str:
    r = requests.post(f"{API}/images?action=initializeUpload", headers=_headers(),
                      json={"initializeUploadRequest": {"owner": owner}}, timeout=60)
    if r.status_code >= 400:
        raise _fail("image upload start", r)
    value = r.json()["value"]
    with open(path, "rb") as f:
        up = requests.put(value["uploadUrl"], data=f.read(), timeout=120,
                          headers={"Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}"})
    if up.status_code >= 400:
        raise _fail("image upload", up)
    return value["image"]


def publish(image_paths: list[str], text: str) -> str:
    """Post one image or a multi-image post to the Company Page. Returns the post link."""
    owner = f"urn:li:organization:{os.environ['LINKEDIN_ORG_ID']}"
    ids = [_upload(p, owner) for p in image_paths[:20]]
    content = ({"media": {"id": ids[0]}} if len(ids) == 1
               else {"multiImage": {"images": [{"id": i} for i in ids]}})
    body = {
        "author": owner,
        "commentary": format_commentary(text),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                         "thirdPartyDistributionChannels": []},
        "content": content,
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    r = requests.post(f"{API}/posts", headers=_headers(), json=body, timeout=60)
    if r.status_code >= 400:
        raise _fail("post", r)
    post_id = r.headers.get("x-restli-id", "")
    return f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else "posted"

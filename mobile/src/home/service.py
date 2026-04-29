from __future__ import annotations

import json
import urllib.request


def fetch_featured_dishes(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "ECAG-Flet-Client"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("featured_dishes", [])
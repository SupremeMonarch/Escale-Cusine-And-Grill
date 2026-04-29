from __future__ import annotations

import json
import urllib.parse
import urllib.request


def fetch_notification_events(base_url: str, since_iso: str | None = None) -> dict:
    endpoint = urllib.parse.urljoin(base_url.rstrip("/") + "/", "mobile/notifications/")
    if since_iso:
        endpoint = f"{endpoint}?since={urllib.parse.quote(since_iso)}"

    req = urllib.request.Request(endpoint, headers={"User-Agent": "ECAG-Flet-Client", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return {
        "events": payload.get("events", []),
        "server_time": payload.get("server_time"),
    }

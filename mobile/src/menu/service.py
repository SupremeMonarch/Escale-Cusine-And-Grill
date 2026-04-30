from __future__ import annotations

import json
from pathlib import Path
import urllib.parse
import urllib.request

import flet as ft


def fetch_menu_data(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "ECAG-Flet-Client"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("categories", [])


def start_checkout(base_url: str, items: list[dict], order_type: str, address: str = "") -> dict:
    endpoint = urllib.parse.urljoin(base_url, "/menu/mobile/checkout/start/")
    payload = {"items": items, "order_type": order_type}
    if order_type == "delivery":
        payload["address"] = address
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ECAG-Flet-Client"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not parsed.get("ok"):
        raise RuntimeError(parsed.get("error", "Checkout start failed"))
    return parsed


def complete_checkout(
    base_url: str,
    order_id: int,
    payment_method: str,
    card_name: str = "",
    card_number: str = "",
    exp_date: str = "",
    cvv: str = "",
) -> dict:
    endpoint = urllib.parse.urljoin(base_url, "/menu/mobile/checkout/complete/")
    payload = {
        "order_id": order_id,
        "payment_method": payment_method,
        "card_name": card_name,
        "card_number": card_number,
        "exp_date": exp_date,
        "cvv": cvv,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ECAG-Flet-Client"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not parsed.get("ok"):
        raise RuntimeError(parsed.get("error", "Checkout completion failed"))
    return parsed


def read_storage_json(page: ft.Page, key: str, fallback):
    try:
        raw = page.client_storage.get(key)
        if raw is None:
            return fallback
        if isinstance(raw, str):
            return json.loads(raw)
        return raw
    except Exception:
        return fallback


def write_storage_json(page: ft.Page, key: str, value) -> None:
    try:
        page.client_storage.set(key, json.dumps(value))
    except Exception:
        pass


def resolve_image_payload(raw_url: str, base_url: str = "http://127.0.0.1:8000") -> dict:
    if not raw_url:
        return {}

    try:
        parsed = urllib.parse.urlparse(raw_url)
        image_url = raw_url
        if not parsed.scheme:
            image_url = urllib.parse.urljoin(base_url, raw_url)
            parsed = urllib.parse.urlparse(image_url)

        # Prefer local bytes for localhost media for reliable desktop rendering.
        if parsed.hostname in {"127.0.0.1", "localhost"} and parsed.path.startswith("/media/"):
            project_root = Path(__file__).resolve().parents[3]
            local_path = project_root / parsed.path.lstrip("/")
            if local_path.exists():
                try:
                    return {"src": local_path.read_bytes()}
                except Exception:
                    return {"src": local_path.as_uri()}

        return {"src": image_url}
    except Exception:
        return {"src": raw_url}

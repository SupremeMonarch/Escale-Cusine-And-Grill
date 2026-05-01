import asyncio
import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("ECAG_API_BASE_URL", "http://192.168.100.12:8000").rstrip("/")
TIMEOUT = 5

def get_headers(token: str) -> dict:
    return {"Authorization": f"Token {token}"}

def _sync_request(method: str, url: str, headers: dict, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    all_headers = {**headers}
    if data is not None:
        all_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception:
        return 0, {}

async def fetch_orders(token: str, staff: bool = False) -> list[dict] | None:
    try:
        path = "/api/menu/orders/" + ("?view=staff" if staff else "")
        status, data = await asyncio.to_thread(_sync_request, "GET", BASE_URL + path, get_headers(token))
        if status and status < 400:
            return data.get("results", [])
        print(f"fetch_orders HTTP error: {status}")
        return None
    except Exception as e:
        print(f"fetch_orders error: {e}")
        return None

async def fetch_reservations(token: str, staff: bool = False) -> list[dict] | None:
    try:
        path = "/api/reservations/bookings/" + ("?view=staff" if staff else "")
        status, data = await asyncio.to_thread(_sync_request, "GET", BASE_URL + path, get_headers(token))
        if status and status < 400:
            return data.get("results", [])
        print(f"fetch_reservations HTTP error: {status}")
        return None
    except Exception as e:
        print(f"fetch_reservations error: {e}")
        return None

async def cancel_reservation(token: str, res_id: int) -> bool:
    try:
        status, _ = await asyncio.to_thread(
            _sync_request, "PATCH",
            f"{BASE_URL}/api/reservations/bookings/{res_id}/",
            get_headers(token),
            {"status": "cancelled"},
        )
        return bool(status and status < 400)
    except Exception as e:
        print(f"cancel_reservation error: {e}")
        return False

async def fetch_profile(token: str) -> dict | None:
    try:
        status, data = await asyncio.to_thread(_sync_request, "GET", BASE_URL + "/api/auth/users/me/", get_headers(token))
        return data if status and status < 400 else None
    except Exception as e:
        print(f"fetch_profile error: {e}")
        return None

async def save_profile(token: str, user_id: int, user_data: dict, profile_data: dict) -> tuple[bool, str]:
    try:
        payload = {**user_data, "profile": profile_data}
        status, data = await asyncio.to_thread(
            _sync_request, "PATCH", BASE_URL + "/api/auth/users/me/", get_headers(token), payload
        )
        if status and status < 400:
            return True, ""
        try:
            msg = "; ".join(
                f"{k}: {v[0] if isinstance(v, list) else v}"
                for k, v in data.items()
            )
        except Exception:
            msg = f"Error {status}"
        return False, msg
    except Exception as e:
        return False, str(e)


async def update_order_status(token: str, order_id: int, status_value: str, staff: bool = False) -> bool:
    try:
        query = "?view=staff" if staff else ""
        status, _ = await asyncio.to_thread(
            _sync_request,
            "PATCH",
            f"{BASE_URL}/api/menu/orders/{order_id}/{query}",
            get_headers(token),
            {"status": status_value},
        )
        return bool(status and status < 400)
    except Exception as e:
        print(f"update_order_status error: {e}")
        return False


async def update_delivery_status(token: str, delivery_id: int | None, status_value: str) -> bool:
    if not delivery_id:
        return False
    try:
        status, _ = await asyncio.to_thread(
            _sync_request,
            "PATCH",
            f"{BASE_URL}/api/menu/deliveries/{delivery_id}/",
            get_headers(token),
            {"delivery_status": status_value},
        )
        return bool(status and status < 400)
    except Exception as e:
        print(f"update_delivery_status error: {e}")
        return False


async def update_takeout_status(token: str, takeout_id: int | None, status_value: str) -> bool:
    if not takeout_id:
        return False
    try:
        status, _ = await asyncio.to_thread(
            _sync_request,
            "PATCH",
            f"{BASE_URL}/api/menu/takeouts/{takeout_id}/",
            get_headers(token),
            {"pickup_status": status_value},
        )
        return bool(status and status < 400)
    except Exception as e:
        print(f"update_takeout_status error: {e}")
        return False


async def update_reservation_status(token: str, reservation_id: int, status_value: str, staff: bool = False) -> bool:
    try:
        query = "?view=staff" if staff else ""
        status, _ = await asyncio.to_thread(
            _sync_request,
            "PATCH",
            f"{BASE_URL}/api/reservations/bookings/{reservation_id}/{query}",
            get_headers(token),
            {"status": status_value},
        )
        return bool(status and status < 400)
    except Exception as e:
        print(f"update_reservation_status error: {e}")
        return False

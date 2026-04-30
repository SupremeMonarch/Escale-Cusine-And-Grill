import httpx

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 5

def get_headers(token: str) -> dict:
    return {"Authorization": f"Token {token}"}

client = httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)

async def fetch_orders(token: str, staff: bool = False) -> list[dict] | None:

    try:
        url = "/api/menu/orders/"
        if staff:
            url += "?view=staff"

        r = await client.get(
            url,
            headers=get_headers(token),
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except httpx.HTTPStatusError as e:
        print(f"fetch_orders HTTP error: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"fetch_orders error: {e}")
        return None

async def fetch_reservations(token: str, staff: bool = False) -> list[dict] | None:
    try:
        url = "/api/reservations/bookings/"
        if staff:
            url += "?view=staff"
        r = await client.get(
            url,
            headers=get_headers(token),
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except httpx.HTTPStatusError as e:
        print(f"fetch_reservations HTTP error: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"fetch_reservations error: {e}")
        return None

async def cancel_reservation(token: str, res_id: int) -> bool:
    try:
        r = await client.patch(
            f"/api/reservations/bookings/{res_id}/",
            headers=get_headers(token),
            json={"status": "cancelled"},
        )
        return r.is_success
    except Exception as e:
        print(f"cancel_reservation error: {e}")
        return False

async def fetch_profile(token: str) -> dict | None:
    try:
        r = await client.get(
            "/api/auth/users/me/",
            headers=get_headers(token),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"fetch_profile error: {e}")
        return None

async def save_profile(token: str, user_id: int, user_data: dict, profile_data: dict) -> tuple[bool, str]:
    try:
        payload = {**user_data, "profile": profile_data}
        r = await client.patch(
            "/api/auth/users/me/",
            headers=get_headers(token),
            json=payload,
        )
        if r.is_success:
            return True, ""
        try:
            errors = r.json()
            msg = "; ".join(
                f"{k}: {v[0] if isinstance(v, list) else v}"
                for k, v in errors.items()
            )
        except Exception:
            msg = f"Error {r.status_code}"
        return False, msg
    except Exception as e:
        return False, str(e)

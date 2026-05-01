from __future__ import annotations

import json
import os
from collections.abc import Callable
from urllib import error, request

from .models import ReservationDraft, ReservationItem, TableItem


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ReservationApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        token_provider: Callable[[], str | None] | None = None,
        timeout_seconds: int = 8,
    ):
        self.base_url = (base_url or os.getenv("ECAG_API_BASE_URL", "http://192.168.100.12:8000")).rstrip("/")
        self.auth_token = auth_token or os.getenv("ECAG_API_TOKEN")
        self.token_provider = token_provider
        self.timeout_seconds = timeout_seconds

    def _resolve_auth_token(self) -> str | None:
        token = self.auth_token
        if self.token_provider:
            try:
                provided = self.token_provider()
                if provided:
                    token = str(provided)
            except Exception:
                pass
        if not token:
            token = os.getenv("ECAG_API_TOKEN")
        return token

    def list_tables(self) -> list[TableItem]:
        payload = self._request_json("GET", "/api/reservations/tables/")
        raw_tables = payload.get("results", payload) if isinstance(payload, dict) else payload
        return [TableItem.from_api(item) for item in raw_tables or []]

    def list_bookings(self, staff_view: bool = False) -> list[ReservationItem]:
        suffix = "?view=staff" if staff_view else ""
        payload = self._request_json("GET", f"/api/reservations/bookings/{suffix}")
        raw_bookings = payload.get("results", payload) if isinstance(payload, dict) else payload
        return [ReservationItem.from_api(item) for item in raw_bookings or []]

    def create_booking(self, draft: ReservationDraft) -> ReservationItem:
        payload = self._request_json("POST", "/api/reservations/bookings/", body=draft.to_payload())
        return ReservationItem.from_api(payload)

    def _request_json(self, method: str, path: str, body: dict | None = None):
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

        token = self._resolve_auth_token()
        if token:
            if token.lower().startswith(("token ", "bearer ")):
                headers["Authorization"] = token
            else:
                headers["Authorization"] = f"Token {token}"

        req = request.Request(
            url=f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="ignore")
            detail = text or exc.reason
            raise ApiError(f"HTTP {exc.code}: {detail}", status_code=exc.code) from exc
        except error.URLError as exc:
            raise ApiError(f"Unable to reach backend: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ApiError(f"Backend returned invalid JSON: {exc}") from exc

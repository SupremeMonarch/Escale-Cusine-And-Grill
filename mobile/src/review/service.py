from __future__ import annotations

import json
import os
from urllib import error, request

from .models import ReviewItem, ReviewSubmission


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ReviewApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        timeout_seconds: int = 8,
    ):
        self.base_url = (base_url or os.getenv("ECAG_API_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.auth_token = auth_token or os.getenv("ECAG_API_TOKEN")
        self.timeout_seconds = timeout_seconds

    def list_reviews(self) -> list[ReviewItem]:
        payload = self._request_json("GET", "/api/review/reviews/")
        if isinstance(payload, dict) and "results" in payload:
            raw_reviews = payload.get("results") or []
        else:
            raw_reviews = payload or []

        reviews = [ReviewItem.from_api(item) for item in raw_reviews]
        reviews.sort(key=lambda item: item.submission_date or "", reverse=True)
        return reviews

    def create_review(self, review: ReviewSubmission) -> ReviewItem:
        payload = self._request_json("POST", "/api/review/reviews/", body=review.to_payload())
        return ReviewItem.from_api(payload)

    def mark_helpful(self, review_id: int) -> int:
        payload = self._request_json("POST", f"/api/review/reviews/{review_id}/helpful/", body={})
        return int(payload.get("helpful", 0))

    def _request_json(self, method: str, path: str, body: dict | None = None):
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
        }

        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

        if self.auth_token:
            if self.auth_token.lower().startswith(("token ", "bearer ")):
                headers["Authorization"] = self.auth_token
            else:
                headers["Authorization"] = f"Token {self.auth_token}"

        req = request.Request(url=url, data=data, headers=headers, method=method)

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

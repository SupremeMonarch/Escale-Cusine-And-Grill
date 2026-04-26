from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(slots=True)
class ReviewItem:
    review_id: int
    user_name: str
    email: str
    review_title: str
    review_text: str
    rating: int
    dishes_ordered: str
    date_of_visit: str | None
    submission_date: str | None
    would_you_recommend: str
    helpful_count: int
    is_verified: bool

    @classmethod
    def from_api(cls, payload: dict) -> "ReviewItem":
        return cls(
            review_id=int(payload.get("review_id", 0)),
            user_name=str(payload.get("user_name", "")),
            email=str(payload.get("email", "")),
            review_title=str(payload.get("review_title", "")),
            review_text=str(payload.get("review_text", "")),
            rating=int(payload.get("rating", 0) or 0),
            dishes_ordered=str(payload.get("dishes_ordered", "")),
            date_of_visit=payload.get("date_of_visit"),
            submission_date=payload.get("submission_date"),
            would_you_recommend=str(payload.get("would_you_recommend", "neutral")),
            helpful_count=int(payload.get("helpful_count", 0) or 0),
            is_verified=bool(payload.get("is_verified", False)),
        )

    @property
    def dishes(self) -> list[str]:
        return [dish.strip() for dish in self.dishes_ordered.split(",") if dish.strip()]

    @property
    def submission_label(self) -> str:
        if not self.submission_date:
            return "Unknown date"
        value = self.submission_date.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%b %d, %Y")
        except ValueError:
            return self.submission_date


@dataclass(slots=True)
class ReviewStats:
    average_rating: float
    total_reviews: int
    counts: dict[int, int]

    @property
    def average_int(self) -> int:
        return int(round(self.average_rating))


@dataclass(slots=True)
class ReviewSubmission:
    user_name: str
    email: str
    review_title: str
    review_text: str
    rating: int
    dishes_ordered: str
    date_of_visit: str | None
    would_you_recommend: str

    def to_payload(self) -> dict:
        return {
            "user_name": self.user_name,
            "email": self.email,
            "review_title": self.review_title,
            "review_text": self.review_text,
            "rating": self.rating,
            "dishes_ordered": self.dishes_ordered,
            "date_of_visit": self.date_of_visit,
            "would_you_recommend": self.would_you_recommend,
        }


def build_review_stats(reviews: Iterable[ReviewItem]) -> ReviewStats:
    data = list(reviews)
    total_reviews = len(data)
    counts = {i: 0 for i in range(1, 6)}

    if not data:
        return ReviewStats(average_rating=0.0, total_reviews=0, counts=counts)

    score_total = 0
    for review in data:
        if 1 <= review.rating <= 5:
            counts[review.rating] += 1
            score_total += review.rating

    return ReviewStats(
        average_rating=round(score_total / total_reviews, 1),
        total_reviews=total_reviews,
        counts=counts,
    )

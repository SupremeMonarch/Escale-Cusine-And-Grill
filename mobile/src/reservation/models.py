from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(slots=True)
class TableItem:
    table_id: int
    table_number: int
    seats: int
    x_position: int = 0
    y_position: int = 0

    @classmethod
    def from_api(cls, payload: dict) -> "TableItem":
        return cls(
            table_id=int(payload.get("table_id", 0) or 0),
            table_number=int(payload.get("table_number", 0) or 0),
            seats=int(payload.get("seats", 2) or 2),
            x_position=int(payload.get("x_position", 0) or 0),
            y_position=int(payload.get("y_position", 0) or 0),
        )

    @property
    def label(self) -> str:
        return f"Table {self.table_number}"

    @property
    def summary_label(self) -> str:
        return f"Table {self.table_number} ({self.seats}-Seater)"


@dataclass(slots=True)
class ReservationItem:
    reservation_id: int
    table_id: int
    table_number: int | None
    table_seats: int | None
    date: str
    time: str
    guest_count: int
    full_name: str
    phone: str
    email: str
    special_requests: str
    status: str

    @classmethod
    def from_api(cls, payload: dict) -> "ReservationItem":
        table = payload.get("table") or {}
        raw_table_id = payload.get("table_id")
        if isinstance(raw_table_id, dict):
            raw_table_id = raw_table_id.get("table_id")
        return cls(
            reservation_id=int(payload.get("reservation_id", 0) or 0),
            table_id=int(raw_table_id or table.get("table_id", 0) or 0),
            table_number=int(table["table_number"]) if table.get("table_number") is not None else None,
            table_seats=int(table["seats"]) if table.get("seats") is not None else None,
            date=str(payload.get("date", "")),
            time=str(payload.get("time", ""))[:5],
            guest_count=int(payload.get("guest_count", 0) or 0),
            full_name=str(payload.get("full_name") or ""),
            phone=str(payload.get("phone") or ""),
            email=str(payload.get("email") or ""),
            special_requests=str(payload.get("special_requests") or ""),
            status=str(payload.get("status") or "pending"),
        )

    def overlaps(self, requested_date: date, requested_time: str) -> bool:
        if self.status == "cancelled" or self.date != requested_date.isoformat():
            return False
        try:
            current_start = datetime.combine(
                requested_date,
                datetime.strptime(self.time[:5], "%H:%M").time(),
            )
            requested_start = datetime.combine(
                requested_date,
                datetime.strptime(requested_time, "%H:%M").time(),
            )
        except ValueError:
            return False
        return not (
            requested_start + timedelta(hours=2) <= current_start
            or requested_start >= current_start + timedelta(hours=2)
        )


@dataclass(slots=True)
class ReservationDraft:
    date: date
    time: str
    guests: int
    table: TableItem
    full_name: str = ""
    phone: str = ""
    email: str = ""
    special_requests: str = ""

    @property
    def display_date(self) -> str:
        return self.date.strftime("%b %d, %Y")

    @property
    def display_time(self) -> str:
        parsed = datetime.strptime(self.time, "%H:%M")
        return parsed.strftime("%I:%M %p").lstrip("0")

    @property
    def confirmation_number(self) -> str:
        seed = f"{self.date:%m%d}{self.table.table_number}{self.guests}"
        return f"ES-{seed}-AMB"

    @property
    def table_summary(self) -> str:
        return self.table.summary_label

    def to_payload(self) -> dict:
        return {
            "table_id": self.table.table_id,
            "date": self.date.isoformat(),
            "time": self.time,
            "guest_count": self.guests,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "special_requests": self.special_requests,
            "status": "confirmed",
        }


def fallback_tables() -> list[TableItem]:
    return [
        TableItem(table_id=i, table_number=i, seats=2 if i in (5, 6, 7, 8, 9) else 4)
        for i in range(1, 16)
    ]


def reservation_times() -> list[str]:
    values: list[str] = []
    current = datetime.combine(date.today(), time(15, 0))
    end = datetime.combine(date.today(), time(22, 0))
    while current <= end:
        values.append(current.strftime("%H:%M"))
        current += timedelta(minutes=15)
    return values

from __future__ import annotations

import re
import os
from collections.abc import Callable
from datetime import date, datetime, timedelta
from urllib.parse import quote, urlencode

import flet as ft

from .models import ReservationDraft, ReservationItem, TableItem, fallback_tables, reservation_times
from .service import ApiError, ReservationApiClient


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"(?=(?:.*\d){7,15})^[0-9()+\-\s]+$")


class ReservationFeature:
    def __init__(
        self,
        page: ft.Page,
        on_navigate: Callable[[str], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ):
        self.page = page
        self.on_navigate = on_navigate
        self.on_back = on_back

        def _token_provider() -> str | None:
            try:
                token = self.page.client_storage.get("auth.token")
                if token:
                    return str(token)
            except Exception:
                pass
            try:
                token = self.page.session.store.get("token")
                if token:
                    return str(token)
            except Exception:
                pass
            return os.getenv("ECAG_API_TOKEN")

        self.client = ReservationApiClient(token_provider=_token_provider)
        self.url_launcher = ft.UrlLauncher()
        self.page.services.append(self.url_launcher)

        self.selected_date = date.today() + timedelta(days=1)
        self.selected_time = "19:30"
        self.guests = 2
        self.selected_table: TableItem | None = None
        self.confirmed_reservation: ReservationItem | None = None
        self.tables: list[TableItem] = []
        self.bookings: list[ReservationItem] = []
        self.available_table_ids: set[int] = set()
        self.backend_note = ""

        self.date_cards = ft.Row(spacing=14, scroll=ft.ScrollMode.AUTO)
        self.guest_text = ft.Text(str(self.guests), size=22, weight=ft.FontWeight.BOLD, color="#34302a")
        self.time_dropdown = ft.Dropdown(
            value=self.selected_time,
            border=ft.InputBorder.NONE,
            text_style=ft.TextStyle(size=22, weight=ft.FontWeight.BOLD, color="#34302a"),
            options=[ft.DropdownOption(key=t, text=t) for t in reservation_times()],
            on_select=self._change_time,
        )
        self.table_plan = ft.Stack(height=430)
        self.table_summary = ft.Container()
        self.feedback_text = ft.Text("", size=13, color="#7a2315")

        self.name_input = self._text_field("Jane Doe", ft.Icons.PERSON_OUTLINE)
        self.phone_input = self._text_field("+1 (555) 000-0000", ft.Icons.PHONE_OUTLINED)
        self.email_input = self._text_field("jane.doe@example.com", ft.Icons.EMAIL_OUTLINED)
        self.requests_input = self._text_field(
            "Allergies, dietary restrictions, or special occasions...",
            ft.Icons.NOTES_OUTLINED,
            multiline=True,
            min_lines=4,
            max_lines=5,
        )

        self.date_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date.today() + timedelta(days=90),
            on_change=self._date_picked,
        )
        self.page.overlay.append(self.date_picker)

    def build_start_view(self) -> ft.Control:
        self._refresh_date_cards()
        return self._screen(
            step=1,
            controls=[
                ft.Container(height=18),
                ft.Text("Reserve Your Table", size=34, weight=ft.FontWeight.BOLD, color="#a63b06"),
                ft.Text("Experience culinary excellence at Escale.", size=16, color="#716a60"),
                ft.Container(height=36),
                self._progress(1),
                ft.Container(height=34),
                self._section_card(
                    [
                        self._section_title(ft.Icons.CALENDAR_MONTH, "Select Date"),
                        self.date_cards,
                    ],
                    padding=22,
                ),
                ft.Row(
                    spacing=18,
                    controls=[
                        ft.Container(expand=True, content=self._guest_card()),
                        ft.Container(expand=True, content=self._time_card()),
                    ],
                ),
                ft.Container(height=42),
                self._outline_button("Show Available Tables", ft.Icons.GRID_VIEW, self._show_tables),
                self._primary_button("Continue to Details", self._continue_from_start),
                self.feedback_text,
            ],
        )

    def build_table_view(self) -> ft.Control:
        self._ensure_data_loaded()
        self._refresh_availability()
        if self.selected_table and self.selected_table.table_id not in self.available_table_ids:
            self.selected_table = None
        if not self.selected_table:
            self.selected_table = next((table for table in self.tables if table.table_id in self.available_table_ids), None)
        self._refresh_table_plan()
        self._refresh_table_summary()

        return self._screen(
            step=1,
            controls=[
                self._modal_header("Select Table", "Restaurant Plan", self._go_back),
                ft.Container(
                    height=470,
                    bgcolor="#f4ead8",
                    border_radius=24,
                    padding=ft.padding.symmetric(horizontal=12, vertical=16),
                    content=self.table_plan,
                ),
                ft.Container(
                    bgcolor="#fff8ef",
                    border_radius=26,
                    padding=ft.padding.symmetric(horizontal=20, vertical=18),
                    content=ft.Column(
                        spacing=18,
                        controls=[
                            self._legend(),
                            self.table_summary,
                            self._primary_button("Confirm Selection", self._confirm_table_selection),
                        ],
                    ),
                ),
                self.feedback_text,
            ],
            top_padding=0,
        )

    def build_details_view(self) -> ft.Control:
        return self._screen(
            step=2,
            controls=[
                ft.Container(height=48),
                ft.Text("Guest Details", size=42, weight=ft.FontWeight.BOLD, color="#a63b06"),
                ft.Text(
                    "Please provide your information to finalise the reservation.",
                    size=19,
                    color="#676056",
                ),
                ft.Container(height=34),
                self._progress(2),
                ft.Container(height=28),
                self._field_label("Full Name"),
                self.name_input,
                self._field_label("Phone Number"),
                self.phone_input,
                self._field_label("Email Address"),
                self.email_input,
                self._field_label("Special Requests", "(Optional)"),
                self.requests_input,
                ft.Container(height=28),
                self.feedback_text,
                self._outline_button("Back to Table Selection", ft.Icons.ARROW_BACK, self._go_back),
                self._primary_button("Complete Reservation", self._complete_reservation),
            ],
        )

    def build_confirmation_view(self) -> ft.Control:
        draft = self._confirmed_draft()
        return self._screen(
            step=3,
            controls=[
                ft.Container(height=70),
                ft.Container(
                    width=112,
                    height=112,
                    border_radius=56,
                    bgcolor="#e9d7b8",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=52,
                        height=52,
                        border_radius=26,
                        bgcolor="#ad4206",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.CHECK, size=34, color="white"),
                    ),
                ),
                ft.Text("Confirmed", size=44, weight=ft.FontWeight.BOLD, color="#a63b06", text_align=ft.TextAlign.CENTER),
                ft.Text(
                    "Your table awaits. We look forward\nto hosting you.",
                    size=20,
                    color="#676056",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=22),
                self._confirmation_card(draft),
                ft.Container(height=10),
                self._calendar_button(draft),
                self._soft_button("Back to Home", self._go_home),
            ],
            horizontal=ft.CrossAxisAlignment.CENTER,
        )

    def _screen(
        self,
        step: int,
        controls: list[ft.Control],
        top_padding: int = 16,
        horizontal: ft.CrossAxisAlignment = ft.CrossAxisAlignment.STRETCH,
    ) -> ft.Control:
        content: list[ft.Control] = []
        content.extend(controls)
        content.append(ft.Container(height=12))

        return ft.Container(
            expand=True,
            bgcolor="#fff3e3",
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Container(
                width=self._content_width(430),
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=18,
                    horizontal_alignment=horizontal,
                    controls=[
                        ft.Container(
                            padding=ft.padding.only(left=24, right=24, top=top_padding),
                            content=ft.Column(spacing=18, horizontal_alignment=horizontal, controls=content),
                        )
                    ],
                ),
            ),
        )

    def _brand_bar(self) -> ft.Control:
        return ft.Container(
            height=72,
            bgcolor="#fff7ed",
            margin=ft.margin.only(left=-24, right=-24, top=-16),
            padding=ft.padding.symmetric(horizontal=22),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Icon(ft.Icons.RESTAURANT, size=28, color="#a63b06"),
                    ft.Text("ESCALE", size=28, weight=ft.FontWeight.BOLD, color="#a63b06"),
                    ft.Container(width=28),
                ],
            ),
        )

    def _app_header(self, back_enabled: bool = False) -> ft.Control:
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK if back_enabled else ft.Icons.MENU,
                    icon_color="#873417",
                    on_click=self._go_back if back_enabled else lambda e: self._show_message("Navigation menu is not connected yet."),
                ),
                ft.Text("Escale", size=26, italic=True, weight=ft.FontWeight.BOLD, color="#a63b06"),
                ft.Container(
                    width=48,
                    height=48,
                    border_radius=24,
                    bgcolor="#efe3ce",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.PERSON, color="#873417"),
                ),
            ],
        )

    def _modal_header(self, title: str, subtitle: str, on_close) -> ft.Control:
        return ft.Container(
            height=104,
            margin=ft.margin.only(left=-24, right=-24),
            padding=ft.padding.symmetric(horizontal=24),
            bgcolor="#fff7ed",
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    self._round_icon(ft.Icons.CLOSE, on_close),
                    ft.Column(
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color="#a63b06"),
                            ft.Text(subtitle, size=16, color="#716a60"),
                        ],
                    ),
                    self._round_icon(ft.Icons.INFO_OUTLINE, lambda e: self._show_message("Tables in dark gray are already occupied for this slot.")),
                ],
            ),
        )

    def _section_card(self, controls: list[ft.Control], padding: int = 18) -> ft.Control:
        return ft.Container(
            bgcolor="#fff1dc",
            border_radius=26,
            padding=padding,
            content=ft.Column(spacing=20, controls=controls),
        )

    def _section_title(self, icon: str, text: str) -> ft.Control:
        return ft.Row(
            spacing=10,
            controls=[
                ft.Icon(icon, size=26, color="#ff7043"),
                ft.Text(text, size=22, weight=ft.FontWeight.BOLD, color="#a63b06"),
            ],
        )

    def _refresh_date_cards(self) -> None:
        start = date.today()
        days = [start + timedelta(days=i) for i in range(1, 15)]
        self.date_cards.controls = [self._date_card(day) for day in days]
        self._safe_update()

    def _date_card(self, day: date) -> ft.Control:
        active = day == self.selected_date
        return ft.Container(
            width=86,
            height=94,
            border_radius=18,
            bgcolor="#e7d6b8" if active else "#f2e6d1",
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(day.strftime("%a").upper(), size=14, weight=ft.FontWeight.BOLD, color="#a63b06" if active else "#6f675c"),
                    ft.Text(str(day.day), size=28, weight=ft.FontWeight.BOLD, color="#a63b06" if active else "#5e574d"),
                    ft.Text(day.strftime("%b"), size=14, color="#a63b06" if active else "#6f675c"),
                ],
            ),
            on_click=lambda e, value=day: self._select_date(value),
        )

    def _guest_card(self) -> ft.Control:
        return self._section_card(
            [
                ft.Icon(ft.Icons.GROUP_OUTLINED, size=30, color="#ff7043"),
                ft.Text("Guests", size=16, color="#716a60", text_align=ft.TextAlign.CENTER),
                ft.Container(
                    height=48,
                    border_radius=24,
                    bgcolor="#f1e4cf",
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        controls=[
                            self._small_circle(ft.Icons.REMOVE, lambda e: self._change_guests(-1)),
                            self.guest_text,
                            self._small_circle(ft.Icons.ADD, lambda e: self._change_guests(1)),
                        ],
                    ),
                ),
            ],
            padding=18,
        )

    def _time_card(self) -> ft.Control:
        return self._section_card(
            [
                ft.Icon(ft.Icons.ACCESS_TIME, size=30, color="#ff7043"),
                ft.Text("Time", size=16, color="#716a60", text_align=ft.TextAlign.CENTER),
                ft.Container(
                    height=52,
                    bgcolor="#eadcc4",
                    padding=ft.padding.symmetric(horizontal=10),
                    content=self.time_dropdown,
                ),
            ],
            padding=18,
        )

    def _progress(self, active_step: int) -> ft.Control:
        controls: list[ft.Control] = []
        for step in range(1, 4):
            active = step == active_step
            controls.append(ft.Container(width=13, height=13, border_radius=7, bgcolor="#ff7043" if active else "#e5d7bc"))
            if step < 3:
                controls.append(ft.Container(width=46, height=4, border_radius=2, bgcolor="#ff7043" if active else "#e5d7bc"))
        return ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=12, controls=controls)

    def _refresh_table_plan(self) -> None:
        # Coordinates mirror the website SVG restaurant plan, scaled for mobile.
        raw_positions = [
            (1, 97.931, 87.430, 32.372, 64.213),
            (2, 97.801, 170.615, 32.372, 64.213),
            (3, 97.931, 254.402, 32.372, 64.213),
            (4, 97.931, 337.914, 32.372, 64.213),
            (5, 215.541, 114.846, 33.494, 36.662),
            (6, 215.691, 175.968, 33.494, 36.662),
            (7, 215.691, 235.921, 33.494, 36.662),
            (8, 215.691, 296.364, 33.494, 36.662),
            (9, 215.691, 356.768, 33.494, 36.662),
            (10, 348.241, 0.505, 32.372, 64.213),
            (11, 348.021, 85.015, 32.372, 64.213),
            (12, 348.021, 169.735, 32.372, 64.213),
            (13, 348.021, 254.456, 32.372, 64.213),
            (14, 348.021, 337.515, 32.372, 64.213),
            (15, 348.021, 421.342, 32.372, 64.213),
        ]
        scale = 0.75
        offset_x = 18
        offset_y = 30

        def sx(value: float) -> float:
            return (value - 55.0) * scale + offset_x

        def sy(value: float) -> float:
            return (value + 24.0) * scale + offset_y

        def sw(value: float) -> float:
            return value * scale

        table_by_number = {table.table_number: table for table in self.tables}
        controls: list[ft.Control] = [
            ft.Container(
                left=sx(55.117),
                top=sy(-23.433),
                width=2,
                height=456.095 * scale,
                bgcolor="#cabca8",
            ),
            ft.Container(
                left=sx(55.399),
                top=sy(432.662),
                width=177.071 * scale,
                height=2,
                bgcolor="#cabca8",
            ),
            ft.Container(
                left=sx(231.868),
                top=sy(433.865),
                width=2,
                height=76.804 * scale,
                bgcolor="#cabca8",
            ),
            ft.Container(
                left=sx(429.949),
                top=sy(-12.845),
                width=2,
                height=522.76 * scale,
                bgcolor="#cabca8",
            ),
            ft.Container(
                left=sx(119.801),
                top=sy(-14.829),
                width=164.995 * scale,
                height=70.098 * scale,
                bgcolor="#e0d7cc",
                border=ft.border.all(1, "#cabca8"),
                alignment=ft.Alignment.CENTER,
                content=ft.Text("Counter", size=15, weight=ft.FontWeight.BOLD, color="#4f4a43"),
            ),
        ]
        for number, left, top, width, height in raw_positions:
            table = table_by_number.get(number)
            if table is None:
                table = TableItem(table_id=number, table_number=number, seats=2 if number in (5, 6, 7, 8, 9) else 4)
            controls.append(
                ft.Container(
                    left=sx(left) - 10,
                    top=sy(top) - 10,
                    width=sw(width) + 20,
                    height=sw(height) + 20,
                    content=self._table_group(table, sw(width), sw(height)),
                )
            )
        self.table_plan.controls = controls
        self._safe_update()

    def _table_group(self, table: TableItem, table_width: float, table_height: float) -> ft.Control:
        horizontal = table.seats == 2
        chair_size = 14
        body_left = 10
        body_top = 10
        body = ft.Container(
            left=body_left,
            top=body_top,
            width=table_width,
            height=table_height,
            content=self._table_tile(table),
        )
        chairs: list[ft.Control]
        if horizontal:
            middle_y = body_top + (table_height - chair_size) / 2
            chairs = [
                ft.Container(left=0, top=middle_y, width=chair_size, height=chair_size, content=self._chair(table)),
                ft.Container(left=body_left + table_width + 6, top=middle_y, width=chair_size, height=chair_size, content=self._chair(table)),
            ]
        else:
            chairs = [
                ft.Container(left=0, top=body_top + 6, width=chair_size, height=chair_size, content=self._chair(table)),
                ft.Container(left=0, top=body_top + table_height - chair_size - 6, width=chair_size, height=chair_size, content=self._chair(table)),
                ft.Container(left=body_left + table_width + 6, top=body_top + 6, width=chair_size, height=chair_size, content=self._chair(table)),
                ft.Container(left=body_left + table_width + 6, top=body_top + table_height - chair_size - 6, width=chair_size, height=chair_size, content=self._chair(table)),
            ]
        return ft.Container(
            content=ft.Stack(controls=[*chairs, body]),
            on_click=(lambda e, value=table: self._select_table(value)) if table.table_id in self.available_table_ids else None,
        )

    def _table_tile(self, table: TableItem) -> ft.Control:
        selected = self.selected_table and self.selected_table.table_id == table.table_id
        available = table.table_id in self.available_table_ids
        color = "#ffc107" if selected else ("#4caf50" if available else "#dc3545")
        text_color = "#4f3300" if selected else "white"
        border = ft.border.all(2 if selected else 1, "#c67500" if selected else ("#388e3c" if available else "#9b1c1c"))
        return ft.Container(
            border_radius=4,
            bgcolor=color,
            border=border,
            shadow=ft.BoxShadow(blur_radius=14, color="#d18145") if selected else None,
            alignment=ft.Alignment.CENTER,
            content=ft.Text(f"T{table.table_number}", size=10, weight=ft.FontWeight.BOLD, color=text_color),
        )

    def _chair(self, table: TableItem) -> ft.Control:
        selected = self.selected_table and self.selected_table.table_id == table.table_id
        available = table.table_id in self.available_table_ids
        color = "#ffb74d" if selected else ("#4caf50" if available else "#dc3545")
        border_color = "#c67500" if selected else ("#388e3c" if available else "#9b1c1c")
        return ft.Container(
            border_radius=7,
            bgcolor=color,
            border=ft.border.all(1, border_color),
        )

    def _legend(self) -> ft.Control:
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            controls=[
                self._legend_item("#4caf50", "Available"),
                self._legend_item("#ffc107", "Selected", border="#c67500"),
                self._legend_item("#dc3545", "Occupied"),
            ],
        )

    def _legend_item(self, color: str, label: str, border: str | None = None) -> ft.Control:
        return ft.Row(
            spacing=8,
            controls=[
                ft.Container(width=18, height=18, border_radius=9, bgcolor=color, border=ft.border.all(1, border or color)),
                ft.Text(label, size=15, color="#6a6258"),
            ],
        )

    def _refresh_table_summary(self) -> None:
        table = self.selected_table
        if not table:
            self.table_summary.content = ft.Text("Select an available table to continue.", color="#716a60")
        else:
            self.table_summary.content = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(table.label, size=20, weight=ft.FontWeight.BOLD, color="#2f2c29"),
                            ft.Text(f"{self._table_display_label(table)} • Seats {table.seats}", size=16, color="#6a6258"),
                        ],
                    ),
                    ft.Container(
                        width=48,
                        height=48,
                        border_radius=24,
                        bgcolor="#fff1dc",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.TABLE_RESTAURANT, color="#a63b06"),
                    ),
                ],
            )
        self.table_summary.bgcolor = "#ffffff"
        self.table_summary.border_radius = 18
        self.table_summary.padding = ft.padding.symmetric(horizontal=18, vertical=16)
        self._safe_update()

    def _confirmation_card(self, draft: ReservationDraft) -> ft.Control:
        return ft.Container(
            bgcolor="#ffffff",
            border_radius=18,
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column(
                spacing=18,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("CONF. NO", size=16, weight=ft.FontWeight.BOLD, color="#676056"),
                            ft.Text(self.confirmed_reservation_label(draft), size=21, weight=ft.FontWeight.BOLD, color="#34302a"),
                        ],
                    ),
                    ft.Divider(color="#e8dcc8"),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            self._confirm_detail(ft.Icons.CALENDAR_MONTH, "DATE", draft.display_date),
                            self._confirm_detail(ft.Icons.ACCESS_TIME, "TIME", draft.display_time),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            self._confirm_detail(ft.Icons.GROUP_OUTLINED, "GUESTS", f"{draft.guests} People"),
                            self._confirm_detail(ft.Icons.TABLE_RESTAURANT, "TABLE", self._table_display_label(draft.table)),
                        ],
                    ),
                ],
            ),
        )

    def _confirm_detail(self, icon: str, label: str, value: str) -> ft.Control:
        return ft.Container(
            width=145,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(spacing=8, controls=[ft.Icon(icon, size=16, color="#70685d"), ft.Text(label, size=14, color="#70685d")]),
                    ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color="#34302a"),
                ],
            ),
        )

    def confirmed_reservation_label(self, draft: ReservationDraft) -> str:
        if self.confirmed_reservation and self.confirmed_reservation.reservation_id:
            return f"RES-{self.confirmed_reservation.reservation_id}"
        return draft.confirmation_number

    def _table_display_label(self, table: TableItem) -> str:
        return f"T{table.table_number} ({table.seats}-Seater)"

    def _bottom_nav(self, active_step: int) -> ft.Control:
        return ft.Container(
            height=92,
            margin=ft.margin.only(left=-24, right=-24, bottom=-18),
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
            bgcolor="#fff8ef",
            border_radius=ft.border_radius.only(top_left=28, top_right=28),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    self._nav_item(ft.Icons.CALENDAR_MONTH, "Reserve", True, self._go_start),
                    self._nav_item(ft.Icons.RESTAURANT_MENU, "Menu", False, lambda e: self._show_message("Menu screen is not connected yet.")),
                    self._nav_item(ft.Icons.EVENT, "Events", False, lambda e: self._show_message("Events screen is not connected yet.")),
                    self._nav_item(ft.Icons.PERSON_OUTLINE, "Profile", False, lambda e: self._show_message("Profile screen is not connected yet.")),
                ],
            ),
        )

    def _nav_item(self, icon: str, label: str, active: bool, on_click) -> ft.Control:
        return ft.Container(
            width=82,
            height=64,
            border_radius=30,
            bgcolor="#f0dfc1" if active else None,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=25, color="#a63b06" if active else "#6f675c"),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_600, color="#a63b06" if active else "#6f675c"),
                ],
            ),
            on_click=on_click,
        )

    def _text_field(self, hint: str, icon: str, **kwargs) -> ft.TextField:
        return ft.TextField(
            hint_text=hint,
            prefix_icon=icon,
            border=ft.InputBorder.UNDERLINE,
            border_color="#d8c8ae",
            focused_border_color="#a63b06",
            bgcolor="#f0e1c8",
            border_radius=10,
            text_style=ft.TextStyle(size=17, color="#34302a"),
            hint_style=ft.TextStyle(size=17, color="#a79c8d"),
            content_padding=ft.padding.symmetric(horizontal=16, vertical=16),
            **kwargs,
        )

    def _field_label(self, label: str, suffix: str = "") -> ft.Control:
        return ft.Text(
            f"{label} {suffix}".strip(),
            size=17,
            weight=ft.FontWeight.BOLD,
            color="#34302a",
        )

    def _primary_button(self, text: str, on_click) -> ft.Control:
        return ft.Container(
            height=62,
            border_radius=31,
            bgcolor="#c84a08",
            alignment=ft.Alignment.CENTER,
            shadow=ft.BoxShadow(blur_radius=20, color="#e8c9a5"),
            content=ft.Text(text, size=19, weight=ft.FontWeight.BOLD, color="white"),
            on_click=on_click,
        )

    def _calendar_button(self, draft: ReservationDraft) -> ft.Control:
        return ft.Container(
            height=62,
            content=ft.ElevatedButton(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.CALENDAR_MONTH, color="white", size=22),
                        ft.Text("Add to Calendar", size=19, weight=ft.FontWeight.BOLD, color="white"),
                    ],
                ),
                on_click=lambda e: self.page.run_task(self._add_to_calendar, e),
                style=ft.ButtonStyle(
                    bgcolor="#c84a08",
                    color="white",
                    shape=ft.RoundedRectangleBorder(radius=31),
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                ),
            ),
        )

    def _outline_button(self, text: str, icon: str, on_click) -> ft.Control:
        return ft.Container(
            height=62,
            border_radius=31,
            border=ft.border.all(2, "#a63b06"),
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
                controls=[ft.Icon(icon, size=24, color="#a63b06"), ft.Text(text, size=19, weight=ft.FontWeight.BOLD, color="#a63b06")],
            ),
            on_click=on_click,
        )

    def _soft_button(self, text: str, on_click) -> ft.Control:
        return ft.Container(
            height=58,
            border_radius=30,
            bgcolor="#ead8b9",
            alignment=ft.Alignment.CENTER,
            content=ft.Text(text, size=18, weight=ft.FontWeight.BOLD, color="#a63b06"),
            on_click=on_click,
        )

    def _small_circle(self, icon: str, on_click) -> ft.Control:
        return ft.Container(
            width=38,
            height=38,
            border_radius=19,
            bgcolor="#fff7ec",
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon, size=18, color="#34302a"),
            on_click=on_click,
        )

    def _round_icon(self, icon: str, on_click) -> ft.Control:
        return ft.Container(
            width=54,
            height=54,
            border_radius=27,
            bgcolor="#f0dfc1",
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon, size=26, color="#873417"),
            on_click=on_click,
        )

    def _select_date(self, value: date) -> None:
        self.selected_date = value
        self.selected_table = None
        self._refresh_date_cards()

    def _date_picked(self, e: ft.ControlEvent) -> None:
        if self.date_picker.value:
            self._select_date(self.date_picker.value)

    def _change_time(self, e: ft.ControlEvent) -> None:
        self.selected_time = self.time_dropdown.value or "19:30"
        self.selected_table = None

    def _change_guests(self, delta: int) -> None:
        self.guests = max(1, min(4, self.guests + delta))
        self.guest_text.value = str(self.guests)
        self.selected_table = None
        self._safe_update()

    def _show_tables(self, e: ft.ControlEvent) -> None:
        self._navigate("/reservation/tables")

    def _continue_from_start(self, e: ft.ControlEvent) -> None:
        if not self.selected_table:
            self._navigate("/reservation/tables")
            return
        self._navigate("/reservation/details")

    def _confirm_table_selection(self, e: ft.ControlEvent) -> None:
        if not self.selected_table:
            self._set_feedback("Please select an available table.", True)
            return
        self._navigate("/reservation/details")

    def _complete_reservation(self, e: ft.ControlEvent) -> None:
        if not self.selected_table:
            self._set_feedback("Please choose a table before completing your reservation.", True)
            self._navigate("/reservation/tables")
            return

        name = (self.name_input.value or "").strip()
        phone = (self.phone_input.value or "").strip()
        email = (self.email_input.value or "").strip()
        special = (self.requests_input.value or "").strip()

        if not name or not phone or not email:
            self._set_feedback("Please complete your name, phone number, and email.", True)
            return
        if not PHONE_RE.match(phone):
            self._set_feedback("Please enter a valid phone number with 7 to 15 digits.", True)
            return
        if not EMAIL_RE.match(email):
            self._set_feedback("Please enter a valid email address.", True)
            return
        if "<" in special or ">" in special or "javascript:" in special.lower():
            self._set_feedback("Please remove HTML or script content from special requests.", True)
            return

        draft = ReservationDraft(
            date=self.selected_date,
            time=self.selected_time,
            guests=self.guests,
            table=self.selected_table,
            full_name=name,
            phone=phone,
            email=email,
            special_requests=special,
        )

        try:
            self.confirmed_reservation = self.client.create_booking(draft)
        except ApiError as exc:
            if exc.status_code in (401, 403):
                self._set_feedback(
                    "Database save failed: authentication was rejected. Please login again and retry.",
                    is_error=True,
                )
            else:
                self._set_feedback(f"Database save failed: {exc}", is_error=True)
            self.confirmed_reservation = None
            return

        self._show_message(f"Reservation saved to database as RES-{self.confirmed_reservation.reservation_id}.")
        self._navigate("/reservation/confirmed")

    def _select_table(self, table: TableItem) -> None:
        self.selected_table = table
        self._refresh_table_plan()
        self._refresh_table_summary()

    def _ensure_data_loaded(self) -> None:
        try:
            self.tables = self.client.list_tables() or fallback_tables()
            self.backend_note = ""
        except ApiError as exc:
            self.tables = fallback_tables()
            self.backend_note = str(exc)
            self._show_message("Using sample tables because the backend is unavailable.", is_error=True)

        try:
            self.bookings = self.client.list_bookings(staff_view=True)
        except ApiError as exc:
            self.bookings = []
            self.backend_note = str(exc)

    def _refresh_availability(self) -> None:
        seat_required = 2 if self.guests <= 2 else 4
        available: set[int] = set()
        for table in self.tables:
            if table.seats != seat_required:
                continue
            conflict = any(
                booking.table_id == table.table_id and booking.overlaps(self.selected_date, self.selected_time)
                for booking in self.bookings
            )
            if not conflict:
                available.add(table.table_id)
        self.available_table_ids = available

    def _draft_or_placeholder(self) -> ReservationDraft:
        table = self.selected_table or TableItem(table_id=8, table_number=8, seats=2)
        return ReservationDraft(
            date=self.selected_date,
            time=self.selected_time,
            guests=self.guests,
            table=table,
            full_name=(self.name_input.value or "").strip(),
            phone=(self.phone_input.value or "").strip(),
            email=(self.email_input.value or "").strip(),
            special_requests=(self.requests_input.value or "").strip(),
        )

    def _confirmed_draft(self) -> ReservationDraft:
        if not self.confirmed_reservation:
            return self._draft_or_placeholder()

        table = self.selected_table
        if self.confirmed_reservation.table_number is not None:
            table = TableItem(
                table_id=self.confirmed_reservation.table_id,
                table_number=self.confirmed_reservation.table_number,
                seats=self.confirmed_reservation.table_seats or (2 if self.confirmed_reservation.guest_count <= 2 else 4),
            )
        elif table is None:
            table = TableItem(
                table_id=self.confirmed_reservation.table_id,
                table_number=self.confirmed_reservation.table_id,
                seats=2 if self.confirmed_reservation.guest_count <= 2 else 4,
            )

        try:
            reservation_date = datetime.strptime(self.confirmed_reservation.date, "%Y-%m-%d").date()
        except ValueError:
            reservation_date = self.selected_date

        return ReservationDraft(
            date=reservation_date,
            time=self.confirmed_reservation.time[:5] or self.selected_time,
            guests=self.confirmed_reservation.guest_count or self.guests,
            table=table,
            full_name=self.confirmed_reservation.full_name,
            phone=self.confirmed_reservation.phone,
            email=self.confirmed_reservation.email,
            special_requests=self.confirmed_reservation.special_requests,
        )

    def _calendar_event_times(self, draft: ReservationDraft) -> tuple[datetime, datetime] | None:
        try:
            start_dt = datetime.combine(draft.date, datetime.strptime(draft.time, "%H:%M").time())
        except ValueError:
            return None

        return start_dt, start_dt + timedelta(hours=2)

    def _calendar_event_details(self, draft: ReservationDraft) -> str:
        confirmation = self.confirmed_reservation_label(draft)
        details = [
            f"Confirmation: {confirmation}",
            f"Guests: {draft.guests}",
            f"Table: {self._table_display_label(draft.table)}",
        ]
        if draft.full_name:
            details.append(f"Name: {draft.full_name}")
        if draft.phone:
            details.append(f"Phone: {draft.phone}")
        if draft.email:
            details.append(f"Email: {draft.email}")
        if draft.special_requests:
            details.append(f"Special requests: {draft.special_requests}")

        return "\n".join(details)

    def _calendar_url(self, draft: ReservationDraft) -> str:
        event_times = self._calendar_event_times(draft)
        if event_times is None:
            return "https://calendar.google.com/calendar/render"

        start_dt, end_dt = event_times
        params = {
            "action": "TEMPLATE",
            "text": "Escale Table Reservation",
            "dates": f"{start_dt:%Y%m%dT%H%M%S}/{end_dt:%Y%m%dT%H%M%S}",
            "details": self._calendar_event_details(draft),
            "location": "Escale Cuisine & Grill",
            "ctz": "Indian/Mauritius",
        }
        return f"https://calendar.google.com/calendar/render?{urlencode(params)}"

    def _android_calendar_intent_url(self, draft: ReservationDraft, package: str | None = None) -> str | None:
        event_times = self._calendar_event_times(draft)
        if event_times is None:
            return None

        start_dt, end_dt = event_times
        extras = {
            "S.title": "Escale Table Reservation",
            "S.description": self._calendar_event_details(draft),
            "S.eventLocation": "Escale Cuisine & Grill",
            "l.beginTime": str(int(start_dt.timestamp() * 1000)),
            "l.endTime": str(int(end_dt.timestamp() * 1000)),
        }
        intent_parts = [
            "intent:#Intent",
            "action=android.intent.action.INSERT",
            "type=vnd.android.cursor.item/event",
        ]
        if package:
            intent_parts.append(f"package={package}")
        for key, value in extras.items():
            intent_parts.append(f"{key}={quote(value, safe='')}")
        intent_parts.append("end")
        return ";".join(intent_parts)

    def _is_android(self) -> bool:
        platform_value = str(getattr(self.page, "platform", "") or "").lower()
        return "android" in platform_value

    async def _add_to_calendar(self, e: ft.ControlEvent | None = None) -> None:
        draft = self._confirmed_draft()
        urls: list[str] = []
        if self._is_android():
            for package in ("com.google.android.calendar", None):
                android_intent = self._android_calendar_intent_url(draft, package)
                if android_intent:
                    urls.append(android_intent)
        urls.append(self._calendar_url(draft))

        last_error: Exception | None = None
        for url in urls:
            print(f"CALENDAR_URL {url}", flush=True)
            try:
                opened = await self.url_launcher.launch_url(url, mode=ft.LaunchMode.EXTERNAL_APPLICATION)
                if opened is False:
                    continue
                self._show_message("Opening calendar event.")
                return
            except Exception as exc:
                last_error = exc
                print(f"CALENDAR_ERROR {exc}", flush=True)

        if last_error:
            self._show_message("Unable to open calendar from this device.", is_error=True)

    def _go_start(self, e: ft.ControlEvent | None = None) -> None:
        self._navigate("/reservation")

    def _go_back(self, e: ft.ControlEvent | None = None) -> None:
        self.feedback_text.value = ""
        if self.on_back:
            self.on_back()
        else:
            self._go_start()

    def _go_home(self, e: ft.ControlEvent | None = None) -> None:
        self._navigate("/")

    def _navigate(self, route: str) -> None:
        self.feedback_text.value = ""
        if self.on_navigate:
            self.on_navigate(route)
        else:
            self.page.go(route)

    def _set_feedback(self, message: str, is_error: bool) -> None:
        self.feedback_text.value = message
        self.feedback_text.color = "#7a2315" if is_error else "#2f6c43"
        self._show_message(message, is_error)

    def _show_message(self, message: str, is_error: bool = False) -> None:
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#7a2315" if is_error else "#2f6c43",
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _safe_update(self) -> None:
        try:
            self.page.update()
        except RuntimeError:
            pass

    def _screen_width(self) -> int:
        width = getattr(self.page, "width", None)
        if isinstance(width, (int, float)) and width > 0:
            return int(width)
        return 390

    def _content_width(self, max_width: int) -> int:
        return max(320, min(max_width, self._screen_width()))

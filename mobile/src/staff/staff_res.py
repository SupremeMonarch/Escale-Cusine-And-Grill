import flet as ft
from datetime import date, datetime, timedelta
from utils.dashboard_api import fetch_reservations, update_reservation_status
from utils.dashboard_utils import (
    COLORS, FONT_FAMILY, FONT_URL,RESERVATION_STATUS,
    build_theme, filter_chip, status_badge, empty_state, loading_spinner,
    get_res_status_colours, secondary_button, format_res_time, format_res_date, is_today_or_future_date
)

CHIP_FILTERS = {
    "All":       None,
    "Confirmed": "confirmed",
    "Seated":    "seated",
    "Completed": "completed",
    "Cancelled": "cancelled",
    "No-Show":   "no-show",
}

class StaffReservationCard(ft.Container):
    def __init__(self, res: dict, on_tap=None):
        super().__init__()
        self.padding      = 20
        self.border_radius = 20
        self.bgcolor      = COLORS["surface_container_lowest"]
        self.border       = ft.Border.all(1, COLORS["card_outline"])
        self.shadow       = ft.BoxShadow(
            spread_radius=0, blur_radius=5,
            offset=ft.Offset(0, 2),
            color=ft.Colors.with_opacity(0.2, COLORS["on_surface"]),
        )


        res_id      = res.get("reservation_id", "")
        status      = res.get("status", "pending")
        guest_count = res.get("guest_count", 0)
        special     = res.get("special_requests") or ""
        table       = res.get("table") or {}
        table_num   = table.get("table_number", "?")
        table_seats = table.get("seats", "?")
        full_name   = res.get("full_name") or "—"
        phone       = res.get("phone") or ""
        date_str    = res.get("date", "")
        time_str    = res.get("time", "")

        badge_bg, badge_text = get_res_status_colours(status)

        header = ft.Row([
            ft.Column([
                ft.Row([
                    ft.Text(
                        f"#RES-{res_id}",
                        size=14, weight=ft.FontWeight.BOLD, color=COLORS["primary"],
                    ),
                    ft.Text(
                        full_name,
                        size=13, weight=ft.FontWeight.W_600, color=COLORS["on_surface"],
                    ),
                ], spacing=8),
                ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE, size=14, color=COLORS["on_surface_variant"]),
                    ft.Text(
                        f"{format_res_date(date_str)},  {format_res_time(time_str)}",
                        size=13, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500,
                    ),
                ], spacing=6),
            ], spacing=2, expand=True),
            status_badge(status.upper(), badge_bg, badge_text),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        details = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=16, color=COLORS["primary"]),
                    ft.Text(
                        f"{guest_count} {'Person' if guest_count == 1 else 'Persons'}",
                        size=12, weight=ft.FontWeight.W_600, color=COLORS["on_surface"],
                    ),
                ], spacing=8),
                ft.Row([
                    ft.Icon(ft.Icons.TABLE_RESTAURANT_OUTLINED, size=16, color=COLORS["primary"]),
                    ft.Text(
                        f"Table {table_num} ({table_seats}-Seater)",
                        size=12, weight=ft.FontWeight.W_600, color=COLORS["on_surface"],
                    ),
                ], spacing=8),
                *(
                    [ft.Row([
                        ft.Icon(ft.Icons.PHONE_OUTLINED, size=16, color=COLORS["primary"]),
                        ft.Text(phone, size=12, weight=ft.FontWeight.W_600, color=COLORS["on_surface"]),
                    ], spacing=8)]
                    if phone else []
                ),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=24, wrap=True),
            padding=ft.Padding.symmetric(vertical=12),
            border=ft.Border.only(
                top=ft.BorderSide(1, COLORS["card_divider"]),
                bottom=ft.BorderSide(1, COLORS["card_divider"]),
            ),
        )

        content_items = [header, details]

        if special.strip():
            content_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color="#7c5400"),
                        ft.Text(
                            f'"{special.strip()}"',
                            size=11, italic=True, color=COLORS["on_surface"], expand=True,
                        ),
                    ], spacing=8),
                    padding=ft.Padding.only(top=4, bottom=2),
                )
            )

        content_items.append(
            ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.EDIT_OUTLINED, size=14, color=COLORS["primary"]),
                        ft.Text("Update Status", size=12,
                                weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                    ], spacing=4),
                    bgcolor=COLORS["surface_container_low"],
                    padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                    border_radius=10,
                    border=ft.Border.all(1, COLORS["card_outline"]),
                    data=res,
                    on_click=on_tap,
                    ink=True,
                ),
            ])
        )

        self.content = ft.Column(content_items, spacing=12)


def build_status_sheet(page: ft.Page, res: dict, on_updated) -> ft.BottomSheet:
    res_id  = res.get("reservation_id", "")
    status  = res.get("status", "pending").lower()
    name    = res.get("full_name") or f"Reservation #{res_id}"
    token = page.session.store.get("token")

    badge_bg, badge_text = get_res_status_colours(status)
    feedback_text = ft.Text("", size=12, color=COLORS["error"])
    saving_ring   = ft.ProgressRing(width=18, height=18, color=COLORS["primary"], visible=False)
    sheet_ref: list = [None]

    def close_sheet(_=None):
        if sheet_ref[0]:
            sheet_ref[0].open = False
            page.update()

    async def on_status_pick(e):
        new_status = e.control.data
        if new_status == status:
            return
        feedback_text.value = ""
        saving_ring.visible = True
        page.update()

        ok = await update_reservation_status(token, res_id, new_status, staff=True)

        saving_ring.visible = False
        if ok:
            close_sheet()
            on_updated()
        else:
            feedback_text.value = "Failed to update. Please try again."
            page.update()

    def status_row(val: str, label: str, bg: str, fg: str) -> ft.Container:
        is_current = val == status
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(label, size=10, weight=ft.FontWeight.BOLD, color=fg),
                        bgcolor=bg,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
                        border_radius=6,
                    ),
                    ft.Text(
                        label, size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["on_surface"],
                        expand=True,
                    ),
                    ft.Icon(
                        ft.Icons.CHECK_ROUNDED if is_current else ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                        size=14,
                        color=fg if is_current else COLORS["on_surface_variant"],
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=14,
            bgcolor=COLORS["surface_container_lowest"],
            border=ft.Border.all(2, fg) if is_current else ft.Border.all(1, COLORS["card_outline"]),
            opacity=0.55 if is_current else 1.0,
            data=val,
            on_click=on_status_pick if not is_current else None,
            ink=not is_current,
        )

    sheet_content = ft.Column(
        [
            # header
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"#RES-{res_id}",
                                            size=16, weight=ft.FontWeight.BOLD,
                                            color=COLORS["primary"],
                                        ),
                                        ft.Row(
                                            [
                                                status_badge(status.upper(), badge_bg, badge_text),
                                                ft.Text(
                                                    name, size=12,
                                                    color=COLORS["on_surface_variant"],
                                                    weight=ft.FontWeight.W_500,
                                                ),
                                            ],
                                            spacing=8,
                                        ),
                                    ],
                                    spacing=6,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(
                            "Select a new status:",
                            size=12, color=COLORS["on_surface_variant"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=12,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            ),
            # status rows
            ft.Container(
                content=ft.Column(
                    [
                        status_row(
                            key,
                            key.replace("-", " ").title(),
                            cfg["bg"],
                            cfg["text"],
                        )
                        for key, cfg in RESERVATION_STATUS.items()
                        if key != "fallback"
                        if key != "pending"
                    ],
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=16),
            ),
            # feedback
            ft.Container(
                content=ft.Row(
                    [feedback_text, saving_ring],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=4),
            ),
            # dismiss
            ft.Container(
                content=secondary_button("Dismiss", on_click=close_sheet),
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    bs = ft.BottomSheet(
        content=ft.Container(
            content=sheet_content,
            bgcolor=COLORS["background"],
            border_radius=ft.BorderRadius(
                top_left=24, top_right=24, bottom_left=0, bottom_right=0,
            ),
            padding=ft.Padding.only(bottom=24),
        ),
        bgcolor=COLORS["background"],
        show_drag_handle=True,
        draggable=True,
    )
    sheet_ref[0] = bs
    return bs


def date_picker_row(page: ft.Page, selected_date_ref: list, on_date_change) -> ft.Row:

    initial_label = "All Upcoming" if selected_date_ref[0] is None else format_res_date(str(selected_date_ref[0]))
    display_text = ft.Text(
        initial_label,
        size=13, weight=ft.FontWeight.W_700, color=COLORS["primary"],
    )

    def on_pick(e: ft.DatePickerEntryModeChangeEvent):
        if e.data:
            selected_date_ref[0] = e.data.date() + timedelta(days=1)
            display_text.value = format_res_date(str(selected_date_ref[0]))
            page.update()
            on_date_change()

    picker_value = datetime.combine(
        selected_date_ref[0] if selected_date_ref[0] is not None else date.today(),
        datetime.min.time(),
    )
    date_picker = ft.DatePicker(
        first_date=datetime(2024, 1, 1),
        last_date=datetime(2030, 12, 31),
        value=picker_value,
        on_change=on_pick,
    )
    page.overlay.append(date_picker)

    datePickerBtn = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, size=14, color=COLORS["primary"]),
            display_text,
        ], spacing=8),
        bgcolor=COLORS["surface_container_low"],
        padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        border_radius=10,
        border=ft.Border.all(1, COLORS["card_outline"]),
        on_click=lambda _: setattr(date_picker, "open", True) or page.update(),
        ink=True,
        shadow=ft.BoxShadow(
            offset=ft.Offset(0, 1), spread_radius=0, blur_radius=1,
            color=ft.Colors.with_opacity(0.2, COLORS["on_surface"]),
        ),
    )

    reset_btn = ft.Container(
        content=ft.Text("Reset", size=13, weight=ft.FontWeight.W_600, color=COLORS["on_surface_variant"]),
        bgcolor=COLORS["surface_container_low"],
        padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        border_radius=10,
        border=ft.Border.all(1, COLORS["card_outline"]),
        on_click=lambda _: reset_date(selected_date_ref, display_text, date_picker, on_date_change, page),
        ink=True,
    )

    return ft.Row([datePickerBtn, reset_btn], spacing=10)


def reset_date(selected_date_ref, display_text, date_picker, on_date_change, page):
    selected_date_ref[0] = None
    display_text.value = "All Upcoming"
    date_picker.value = datetime.combine(date.today(), datetime.min.time())
    page.update()
    on_date_change()


def get_staff_res_view(page: ft.Page):
    token = page.session.store.get("token")

    # State
    all_reservations: list[dict] = []
    active_filter: list[str | None] = [None]
    selected_date: list[date] = [None]  # None = show all upcoming by default

    cards_column  = ft.Column(controls=[loading_spinner()], spacing=16)
    chip_refs: dict[str, ft.Container] = {}

    count_text = ft.Text("", size=13, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_600)

    def date_key(r: dict) -> str:
        return str(r.get("date", ""))

    def apply_filter():
        filter_val  = active_filter[0]

        # 1. Filter by date — None means "show all upcoming"
        if selected_date[0] is None:
            date_filtered = list(all_reservations)  # already filtered to today+
            scope_label   = "upcoming"
        else:
            date_str      = str(selected_date[0])
            date_filtered = [r for r in all_reservations if date_key(r) == date_str]
            scope_label   = "for the day"

        # 2. Filter by status chip
        filtered = date_filtered if filter_val is None else [
            r for r in date_filtered if r.get("status", "").lower() == filter_val
        ]

        # Update count line
        total   = len(date_filtered)
        showing = len(filtered)
        count_text.value = (
            f"{showing} reservation{'s' if showing != 1 else ''}"
            + (f" · {total} total {scope_label}" if filter_val else "")
        )

        cards_column.controls = (
            [StaffReservationCard(r, on_tap=open_status_sheet) for r in filtered]
            if filtered
            else [empty_state("No reservations for this date / filter.", ft.Icons.EVENT_BUSY_OUTLINED)]
        )
        page.update()

    def on_chip_click(e):
        label = e.control.data
        active_filter[0] = CHIP_FILTERS[label]
        for lbl, chip in chip_refs.items():
            is_active = CHIP_FILTERS[lbl] == active_filter[0]
            chip.bgcolor        = COLORS["primary"] if is_active else COLORS["surface_container_low"]
            chip.content.color  = COLORS["white"] if is_active else COLORS["on_surface_variant"]
            chip.content.weight = ft.FontWeight.BOLD if is_active else ft.FontWeight.W_600
        apply_filter()

    def render_chips() -> ft.Row:
        chips = []
        for label in CHIP_FILTERS:
            is_active = CHIP_FILTERS[label] == active_filter[0]
            chip = filter_chip(label, is_active, on_click=on_chip_click)
            chip_refs[label] = chip
            chips.append(chip)
        return ft.Row(chips, scroll=ft.ScrollMode.HIDDEN, spacing=10)


    def open_status_sheet(e):
        res = e.control.data
        sheet = build_status_sheet(page, res, on_updated=reload_reservations)
        page.overlay.append(sheet)
        sheet.open = True
        page.update()


    async def load_reservations():
        cards_column.controls = [loading_spinner()]
        page.update()

        data = await fetch_reservations(token, True)

        if data is None:
            cards_column.controls = [
                empty_state(
                    "Couldn't reach the server.\nCheck your connection.",
                    ft.Icons.WIFI_OFF_OUTLINED,
                )
            ]
            page.update()
            return

        all_reservations.clear()
        all_reservations.extend(r for r in data if is_today_or_future_date(r.get("date", "")))
        apply_filter()

    def reload_reservations():
        page.run_task(load_reservations)

    page.run_task(load_reservations)

    def on_date_change():
        apply_filter()

    date_row = date_picker_row(page, selected_date, on_date_change)

    chips_row = render_chips()

    main_content = ft.Column(
        [
            ft.Column([
                ft.Text(
                    "Reservations",
                    size=24, weight=ft.FontWeight.W_800, color=COLORS["on_surface"],
                ),
                ft.Text(
                    "Manage today's and upcoming bookings",
                    size=14, color=COLORS["on_surface_variant"],
                ),
            ], spacing=4),

            ft.Divider(height=1, color=ft.Colors.TRANSPARENT),

            ft.Column([
                ft.Text(
                    "FILTER BY DATE",
                    size=11, weight=ft.FontWeight.W_700,
                    color=COLORS["on_surface_variant"],
                ),
                date_row,
            ], spacing=8),
            chips_row,
            count_text,
            cards_column,
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Column([
        ft.Container(
            content=main_content,
            padding=ft.Padding.only(left=24, right=24, top=16, bottom=24),
            expand=True,
        )
    ], scroll=ft.ScrollMode.AUTO, expand=True)


if __name__ == "__main__":
    async def main(page: ft.Page):
        page.title   = "Escale – Staff Reservations"
        page.bgcolor = COLORS["background"]
        page.padding = 0
        page.fonts   = {FONT_FAMILY: FONT_URL}
        page.theme   = build_theme()

        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color=COLORS["primary"]),
                    ft.Text("Escale Staff", size=24, weight=ft.FontWeight.BOLD,
                            color=COLORS["on_surface"]),
                ]),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON), radius=20),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding.only(left=24, right=24, top=10, bottom=10),
            bgcolor=COLORS["background"],
        )

        page.add(ft.Column([header, get_staff_res_view(page)], spacing=0, expand=True))

    ft.app(main)

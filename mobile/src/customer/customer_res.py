import flet as ft
from utils.dashboard_api import fetch_reservations, cancel_reservation
from utils.dashboard_utils import (
    COLORS, FONT_FAMILY, FONT_URL, NON_CANCELLABLE_STATUSES,
    build_theme, filter_chip, status_badge, empty_state, loading_spinner,
    get_res_status_colours, format_res_date, format_res_time,
)

CHIP_FILTERS = {
    "All"      : None,
    "Confirmed": "confirmed",
    "Completed": "completed",
    "Cancelled": "cancelled",
}

class ReservationCard(ft.Container):
    def __init__(self, res: dict, on_cancel=None):
        super().__init__()
        self.padding = 20
        self.border_radius = 20
        self.bgcolor = COLORS["surface_container_lowest"]
        self.border = ft.Border.all(1, COLORS["card_outline"])
        self.shadow = ft.BoxShadow(
            spread_radius=0,
            blur_radius=5,
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

        badge_bg, badge_text = get_res_status_colours(status)

        header = ft.Row([
            ft.Column([
                ft.Text(f"#RES-{res_id}", size=14, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE, size=14, color=COLORS["on_surface_variant"]),
                    ft.Text(
                        f"{format_res_date(res.get('date', ''))}, {format_res_time(res.get('time', ''))}",
                        size=13, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500,
                    ),
                ], spacing=6),
            ], spacing=2),
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
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=40),
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
                    padding=ft.Padding.only(top=4),
                )
            )

        if status not in NON_CANCELLABLE_STATUSES and on_cancel:
            content_items.append(ft.Row([
                ft.Container(
                    content=ft.Text(
                        "Cancel Reservation", size=12,
                        weight=ft.FontWeight.W_600, color=ft.Colors.ERROR,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ERROR),
                    padding=ft.Padding.symmetric(vertical=8),
                    border_radius=100,
                    alignment=ft.alignment.Alignment(0,0),
                    on_click=lambda _, rid=res_id: on_cancel(rid),
                    expand=True,
                )
            ]))

        self.content = ft.Column(content_items, spacing=12)

def get_res_view(page: ft.Page):
    token = page.session.store.get("token")

    all_reservations: list[dict] = []
    active_filter: list[str | None] = [None]

    cards_column = ft.Column(controls=[loading_spinner()], spacing=20)
    chip_refs: dict[str, ft.Container] = {}

    def apply_filter():
        filter_val = active_filter[0]
        filtered = all_reservations if filter_val is None else [
            r for r in all_reservations if r.get("status", "").lower() == filter_val
        ]
        cards_column.controls = (
            [ReservationCard(r, on_cancel=handle_cancel) for r in filtered]
            if filtered else [empty_state("No reservations found for this filter.",
                                         ft.Icons.EVENT_BUSY_OUTLINED)]
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

    def handle_cancel(res_id: int):
        async def do_cancel(_):
            dialog.open = False
            page.update()

            # Optimistic update
            for r in all_reservations:
                if r.get("reservation_id") == res_id:
                    r["status"] = "cancelled"
                    break
            apply_filter()

            # Revert on failure
            success = await cancel_reservation(token, res_id)
            if not success:
                await load_reservations()

        def dismiss(_):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Cancel Reservation",
                weight=ft.FontWeight.W_700, color=COLORS["on_surface"],
            ),
            content=ft.Text(
                f"Are you sure you want to cancel reservation #{res_id}?\nThis cannot be undone.",
                color=COLORS["on_surface_variant"],
            ),
            actions=[
                ft.TextButton(
                    "No, Keep it", on_click=dismiss,
                    style=ft.ButtonStyle(color=COLORS["primary"]),
                ),
                ft.TextButton(
                    "Yes, Cancel",
                    on_click=lambda e: page.run_task(do_cancel, e),
                    style=ft.ButtonStyle(color=ft.Colors.ERROR),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    async def load_reservations():
        data = await fetch_reservations(token)
        if data is None:
            cards_column.controls = [
                empty_state("Couldn't reach the server.\nCheck your connection.",
                            ft.Icons.EVENT_BUSY_OUTLINED)
            ]
            page.update()
            return
        all_reservations.clear()
        all_reservations.extend(data)
        apply_filter()

    page.run_task(load_reservations)

    main_content = ft.Column(
        [
            ft.Column([
                ft.Text("My Reservations", size=24, weight=ft.FontWeight.W_800,
                        color=COLORS["on_surface"]),
                ft.Text("Track and manage your table bookings", size=14,
                        color=COLORS["on_surface_variant"]),
            ], spacing=4),

            ft.Divider(height=1, color=ft.Colors.TRANSPARENT),

            render_chips(),
            cards_column,
        ],
        spacing=20,
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
        page.title   = "Escale - My Reservations"
        page.bgcolor = COLORS["background"]
        page.padding = 0
        page.fonts   = {FONT_FAMILY: FONT_URL}
        page.theme   = build_theme()

        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color=COLORS["primary"]),
                    ft.Text("Escale", size=24, weight=ft.FontWeight.BOLD, color=COLORS["on_surface"]),
                ]),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON), radius=20),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding.only(left=24, right=24, top=10, bottom=10),
            bgcolor=COLORS["background"],
        )
        page.add(ft.Column([header, get_res_view(page)], spacing=0, expand=True))

    ft.app(main)

import asyncio
import flet as ft
from utils.dashboard_api import fetch_orders, fetch_reservations
from utils.dashboard_utils import (
    COLORS, FONT_FAMILY, FONT_URL,
    build_theme, stat_card, empty_state, loading_spinner, get_res_status_colours,
    status_badge, order_type_badge, get_order_status_colours,
    format_order_date, get_item_name, format_res_date, format_res_time,
)

def count_active_deliveries(orders: list[dict]) -> int:
    return sum(
        1 for o in orders
        if o.get("order_type", "").lower() == "delivery"
        and (o.get("delivery") or {}).get("delivery_status") not in ("delivered", None)
    )

def count_upcoming_reservations(reservations: list[dict]) -> int:
    return sum(
        1 for r in reservations
        if r.get("status", "").lower() in ("pending", "confirmed")
    )

class MiniOrderCard(ft.Container):
    def __init__(self, order: dict):
        super().__init__()
        self.padding = 16
        self.border_radius = 16
        self.bgcolor = COLORS["surface"]
        self.border = ft.Border.all(1, COLORS["card_outline"])
        self.margin = ft.Margin.only(bottom=8)
        self.shadow = ft.BoxShadow(
            offset=ft.Offset(0, 2),
            spread_radius=0,
            blur_radius=1,
            color=ft.Colors.with_opacity(0.2, COLORS["on_surface"]),
        )

        item_names = ", ".join(
            get_item_name(i.get("item")) for i in order.get("items", [])
        ) or "—"

        status_label, status_bg, status_text = get_order_status_colours(order)
        order_type = order.get("order_type", "")

        header = ft.Row([
            ft.Text(
                f"#{order.get('order_id_str', '???')}",
                size=13, weight=ft.FontWeight.BOLD, color=COLORS["primary"]
            ),
            ft.Text(
                format_order_date(order.get("order_date", "")),
                size=11, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        items_text = ft.Text(
            item_names, size=11, color=COLORS["on_surface_variant"],
            italic=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS
        )

        footer = ft.Row([
            ft.Text(
                f"Rs {order.get('total', '0.00')}",
                size=14, weight=ft.FontWeight.W_800, color=COLORS["on_surface"]
            ),
            ft.Row(
                [
                    order_type_badge(order_type),
                    status_badge(status_label, status_bg, status_text),
                ],
                spacing=6,
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.content = ft.Column([
            header,
            items_text,
            ft.Divider(height=1, color=COLORS["card_divider"]),
            footer,
        ], spacing=10)


class MiniResCard(ft.Container):
    def __init__(self, res: dict):
        super().__init__()
        self.padding = 16
        self.border_radius = 16
        self.bgcolor = COLORS["surface"]
        self.border = ft.Border.all(1, COLORS["card_outline"])
        self.margin = ft.Margin.only(bottom=8)
        self.shadow = ft.BoxShadow(
            offset=ft.Offset(0, 2),
            spread_radius=0,
            blur_radius=1,
            color=ft.Colors.with_opacity(0.2, COLORS["on_surface"]),
        )

        status    = res.get("status", "pending")
        badge_bg, badge_text = get_res_status_colours(status)
        table_num = (res.get("table") or {}).get("table_number", "?")
        guests    = res.get("guest_count", "?")

        header = ft.Row([
            ft.Row([
                ft.Text(f"#RES-{res.get('reservation_id', '???')}",
                        size=13, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                ft.Text(f" • {guests} Guests", size=11, color=COLORS["on_surface_variant"])
            ]),
            ft.Container(
                content=ft.Text(status.upper(), size=8, weight=ft.FontWeight.BOLD, color=badge_text),
                bgcolor=badge_bg,
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                border_radius=6,
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        details = ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=13, color=COLORS["on_surface_variant"]),
                ft.Text(
                    format_res_date(res.get("date", "")),
                    size=11, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500
                ),
            ], spacing=5),
            ft.Row([
                ft.Icon(ft.Icons.SCHEDULE, size=13, color=COLORS["on_surface_variant"]),
                ft.Text(
                    format_res_time(res.get("time", "")),
                    size=11, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500
                ),
            ], spacing=5),
            ft.Row([
                ft.Icon(ft.Icons.TABLE_RESTAURANT_OUTLINED, size=13, color=COLORS["on_surface_variant"]),
                ft.Text(
                    f"Table {table_num}",
                    size=11, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500
                ),
            ], spacing=5),
        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)

        self.content = ft.Column([
            header,
            ft.Divider(height=1, color=COLORS["card_divider"]),
            details,
        ], spacing=10)

def get_overview_view(page: ft.Page, navigate_to=None):
    token = page.session.store.get("token")

    delivery_count_ref = ft.Ref[ft.Text]()
    res_count_ref      = ft.Ref[ft.Text]()

    orders_cards_col = ft.Column(controls=[loading_spinner()], spacing=0)
    res_cards_col    = ft.Column(controls=[loading_spinner()], spacing=0)

    # --- Tab ---
    tabs = ft.Tabs(
        selected_index=0,
        length=2,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tab_alignment=ft.TabAlignment.CENTER,
                    divider_color=COLORS["background"],
                    indicator_color=COLORS["primary"],
                    label_color=COLORS["on_surface"],
                    unselected_label_color=COLORS["on_surface_variant"],
                    tabs=[
                        ft.Tab(label="Orders"),
                        ft.Tab(label="Reservations"),
                    ]
                ),
                ft.TabBarView(
                    height=2000,
                    width=page.width,

                    controls=[
                        ft.Container(
                            content=orders_cards_col,
                            padding=ft.Padding.only(top=12),
                        ),
                        ft.Container(
                            content=res_cards_col,
                            padding=ft.Padding.only(top=12),
                        ),
                    ],
                ),
            ],
        ),
    )

    # --- Stat cards ---
    delivery_stat = stat_card(
        ft.Icons.LOCAL_SHIPPING_OUTLINED, "ACTIVE DELIVERY",
        delivery_count_ref, COLORS["surface"],COLORS["surface_container_low"], COLORS["primary"]
    )
    res_stat = stat_card(
        ft.Icons.CALENDAR_MONTH_OUTLINED, "UPCOMING BOOKINGS",
        res_count_ref, COLORS["surface_container_low"],"#fde4d3", "#7c5400"
    )

    # --- Quick action buttons ---
    def overview_btn(label, icon, on_click, primary=False) -> ft.Button:
        return ft.Button(
            content=ft.Row([
                ft.Icon(icon, size=16),
                ft.Text(label, size=13),
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER),
            on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=COLORS["primary"] if primary else COLORS["surface_container_low"],
                color="#FAFAFA" if primary else COLORS["on_surface_variant"],
                side=None if primary else ft.BorderSide(1, COLORS["card_outline"]),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            expand=True, height=40,
        )

    action_row_1 = ft.Container(content=ft.Row([

        overview_btn("Order Food", ft.Icons.RESTAURANT_MENU,
                    lambda _: navigate_to(1) if navigate_to else None, primary=True),

        overview_btn("Book Table", ft.Icons.CALENDAR_TODAY,
                    lambda _: navigate_to(2) if navigate_to else None),

    ], spacing=10))

    async def load_data():
        orders, reservations = await asyncio.gather(
            fetch_orders(token),
            fetch_reservations(token),
        )
        orders       = orders       or []
        reservations = reservations or []

        if delivery_count_ref.current:
            delivery_count_ref.current.value = f"{count_active_deliveries(orders):02d}"
        if res_count_ref.current:
            res_count_ref.current.value = f"{count_upcoming_reservations(reservations):02d}"

        orders_cards_col.controls = (
            [MiniOrderCard(o) for o in orders[:3]]
            if orders else [empty_state("No orders yet.", ft.Icons.RECEIPT_LONG_OUTLINED)]
        )

        upcoming    = [r for r in reservations if r.get("status") in ("pending", "confirmed")]
        display_res = upcoming[:3] if upcoming else reservations[:3]
        res_cards_col.controls = (
            [MiniResCard(r) for r in display_res]
            if display_res else [empty_state("No upcoming reservations.", ft.Icons.EVENT_BUSY_OUTLINED)]
        )

        page.update()

    page.run_task(load_data)

    # --- Layout ---
    layout_content = ft.Column([
        ft.Text("My Overview", size=24, weight=ft.FontWeight.W_800, color=COLORS["on_surface"]),
        ft.Row([delivery_stat, res_stat], spacing=12),
        action_row_1,
        tabs
    ], spacing=20)

    return ft.Column([
        ft.Container(
            content=layout_content,
            padding=ft.Padding.only(left=24, right=24, top=16, bottom=24),
        )
    ], scroll=ft.ScrollMode.AUTO, expand=True)


if __name__ == "__main__":
    async def main(page: ft.Page):
        page.title      = "Escale Dashboard"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor    = COLORS["background"]
        page.padding    = 0
        page.fonts      = {FONT_FAMILY: FONT_URL}
        page.theme      = build_theme()

        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color=COLORS["primary"]),
                    ft.Text("Escale", size=24, weight=ft.FontWeight.BOLD, color=COLORS["on_surface"]),
                ]),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON), radius=20),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding.only(left=24, right=24, top=10, bottom=10),
        )

        page.add(ft.Column([header, get_overview_view(page)], spacing=0, expand=True))

    ft.run(main)

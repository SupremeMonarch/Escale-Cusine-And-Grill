import flet as ft
from utils.dashboard_api import fetch_orders
from utils.dashboard_utils import (
    COLORS, FONT_FAMILY, FONT_URL,
    build_theme, filter_chip, status_badge, empty_state, loading_spinner,
    order_type_badge, get_order_status_colours, format_order_date, get_item_name
)

CHIP_FILTERS = {
    "All":      None,
    "Dine-in":  "dine in",
    "Delivery": "delivery",
    "Takeout":  "pick up",
}

class OrderCard(ft.Container):
    def __init__(self, order: dict):
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

        status_label, status_bg, status_text = get_order_status_colours(order)
        order_type = order.get("order_type", "")

        items = [
            (
                f"{i.get('quantity', 1)}x {get_item_name(i.get('item'))}",
                f"Rs {i.get('subtotal', '0.00')}",
            )
            for i in order.get("items", [])
        ] or [("—", "")]

        def item_row(qty_name, price):
            return ft.Row([
                ft.Text(qty_name, size=11, weight=ft.FontWeight.W_500, color=COLORS["on_surface_variant"]),
                ft.Text(price,    size=11, weight=ft.FontWeight.W_500, color=COLORS["on_surface_variant"]),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        header = ft.Row([
            ft.Column([
                ft.Text(
                    f"#{order.get('order_id_str', 'ORD-???')}",
                    size=14, weight=ft.FontWeight.BOLD, color=COLORS["primary"]
                ),
                ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE, size=14, color=COLORS["on_surface_variant"]),
                    ft.Text(
                        format_order_date(order.get("order_date", "")),
                        size=13, color=COLORS["on_surface_variant"], weight=ft.FontWeight.W_500
                    ),
                ], spacing=6),
            ], spacing=2),
            ft.Row(
                [
                    order_type_badge(order_type),
                    status_badge(status_label, status_bg, status_text),
                ],
                spacing=6,
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        items_list = ft.Container(
            content=ft.Column([item_row(i[0], i[1]) for i in items], spacing=4),
            padding=ft.Padding.symmetric(vertical=12, horizontal=10),
            border=ft.Border.only(
                top=ft.BorderSide(1, COLORS["card_divider"]),
                bottom=ft.BorderSide(1, COLORS["card_divider"]),
            ),
        )

        footer = ft.Row([
            ft.Text(
                f"Rs {order.get('total', '0.00')}",
                size=16, weight=ft.FontWeight.W_800, color=COLORS["on_surface"],
                margin=ft.Margin(right=10),
            ),
        ], alignment=ft.MainAxisAlignment.END)

        self.content = ft.Column([header, items_list, footer], spacing=12)


def get_orders_view(page: ft.Page):
    token = page.session.store.get("token")

    all_orders: list[dict] = []
    active_filter: list[str | None] = [None]

    cards_column = ft.Column(controls=[loading_spinner()], spacing=20)
    chip_refs: dict[str, ft.Container] = {}

    def apply_filter():
        filter_val = active_filter[0]
        filtered = all_orders if filter_val is None else [
            o for o in all_orders if o.get("order_type", "").lower() == filter_val
        ]
        cards_column.controls = (
            [OrderCard(o) for o in filtered]
            if filtered else [empty_state("No orders found for this filter.")]
        )
        page.update()

    def on_chip_click(e):
        label = e.control.data
        active_filter[0] = CHIP_FILTERS[label]
        for lbl, chip in chip_refs.items():
            is_active = CHIP_FILTERS[lbl] == active_filter[0]
            chip.bgcolor       = COLORS["primary"] if is_active else COLORS["surface_container_low"]
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

    async def load_orders():
        data = await fetch_orders(token)
        if data is None:
            cards_column.controls = [
                empty_state("Couldn't reach the server.\nCheck your connection.")
            ]
            page.update()
            return
        all_orders.clear()
        all_orders.extend(data)
        apply_filter()

    page.run_task(load_orders)

    main_content = ft.Column(
        [
            ft.Column([
                ft.Text("My Orders", size=24, weight=ft.FontWeight.W_800,
                        color=COLORS["on_surface"]),
                ft.Text("Track and manage your recent culinary journeys",size=14,
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
        page.title   = "Escale - My Orders"
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

        page.add(ft.Column([header, get_orders_view(page)], spacing=0, expand=True))

    ft.run(main)

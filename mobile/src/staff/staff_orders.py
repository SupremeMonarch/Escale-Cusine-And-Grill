import flet as ft
from utils.dashboard_api import fetch_orders, update_order_status, update_delivery_status, update_takeout_status
from utils.dashboard_utils import (
    COLORS, FONT_FAMILY, FONT_URL,DINE_IN,  DELIVERY, TAKEOUT,
    build_theme, filter_chip, status_badge, empty_state, loading_spinner,
    secondary_button, get_order_status_colours, order_type_badge,
    format_order_date, get_item_name, is_today
)

CHIP_FILTERS = {
    "All":      None,
    "Dine-in":  "dine in",
    "Delivery": "delivery",
    "Takeout":  "pick up",
}

def build_status_sheet(page: ft.Page, order: dict, on_updated) -> ft.BottomSheet:
    order_type = order.get("order_type", "").lower()
    order_id   = order.get("id")
    token      = page.session.store.get("token")

    if order_type == "dine in":
        statuses  = DINE_IN
        patch_key = "order"
        nested_id = None
    elif order_type == "delivery":
        statuses  = DELIVERY
        patch_key = "delivery"
        nested_id = (order.get("delivery") or {}).get("id")
    else:
        statuses  = TAKEOUT
        patch_key = "takeout"
        nested_id = (order.get("takeout") or {}).get("id")

    current_label, current_bg, current_text = get_order_status_colours(order)
    feedback_text = ft.Text("", size=12, color=COLORS["error"])
    saving_ring   = ft.ProgressRing(width=18, height=18, color=COLORS["primary"], visible=False)
    sheet_ref: list = [None]

    def close_sheet(_=None):
        if sheet_ref[0]:
            sheet_ref[0].open = False
            page.update()

    async def on_status_pick(e):
        new_status = e.control.data
        feedback_text.value = ""
        saving_ring.visible = True
        page.update()

        if patch_key == "order":
            ok = await update_order_status(token, order_id, new_status, staff=True)
        elif patch_key == "delivery":
            ok = await update_delivery_status(token, nested_id, new_status)
        else:
            ok = await update_takeout_status(token, nested_id, new_status)

        saving_ring.visible = False
        if ok:
            close_sheet()
            on_updated()
        else:
            feedback_text.value = "Failed to update. Please try again."
            page.update()

    def status_row(key: str) -> ft.Container:
        label, bg, txt   = statuses[key]
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(label, size=10, weight=ft.FontWeight.BOLD, color=txt),
                        bgcolor=bg,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
                        border_radius=6,
                    ),
                    ft.Text(
                        label, size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["on_surface"],
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD_IOS_ROUNDED, size=14,
                            color=COLORS["on_surface_variant"]),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=14,
            bgcolor=COLORS["surface_container_lowest"],
            border=ft.Border.all(1, COLORS["card_outline"]),
            data=key,
            on_click=on_status_pick,
            ink=True,
        )

    sheet_content = ft.Column(
        [
            # sheet header
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"#{order.get('order_id_str', 'ORD-???')}",
                                            size=16, weight=ft.FontWeight.BOLD,
                                            color=COLORS["primary"],
                                        ),
                                        ft.Row(
                                            [
                                                order_type_badge(order_type),
                                                status_badge(current_label, current_bg, current_text),
                                            ],
                                            spacing=6,
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
                content=ft.Column([status_row(k) for k in statuses], spacing=8),
                padding=ft.Padding.symmetric(horizontal=16),
            ),
            # feedback / spinner
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


class StaffOrderCard(ft.Container):
    def __init__(self, order: dict, on_tap):
        super().__init__()
        self.padding       = 20
        self.border_radius = 20
        self.bgcolor       = COLORS["surface_container_lowest"]
        self.border        = ft.Border.all(1, COLORS["card_outline"])
        self.shadow        = ft.BoxShadow(
            spread_radius=0, blur_radius=5, offset=ft.Offset(0, 2),
            color=ft.Colors.with_opacity(0.2, COLORS["on_surface"]),
        )

        order_type = order.get("order_type", "")
        status_label, status_bg, status_text = get_order_status_colours(order)

        items = [
            (
                f"{i.get('quantity', 1)}x {get_item_name(i.get('item'))}",
                f"Rs {i.get('subtotal', '0.00')}",
            )
            for i in order.get("items", [])
        ] or [("—", "")]

        def item_row(qty_name, price):
            return ft.Row(
                [
                    ft.Text(qty_name, size=11, weight=ft.FontWeight.W_500,
                            color=COLORS["on_surface_variant"]),
                    ft.Text(price,    size=11, weight=ft.FontWeight.W_500,
                            color=COLORS["on_surface_variant"]),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            f"#{order.get('order_id_str', 'ORD-???')}",
                            size=14, weight=ft.FontWeight.BOLD, color=COLORS["primary"],
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.SCHEDULE, size=14,
                                        color=COLORS["on_surface_variant"]),
                                ft.Text(
                                    format_order_date(order.get("order_date", "")),
                                    size=13, color=COLORS["on_surface_variant"],
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=6,
                        ),

                    ],
                    spacing=3,
                ),
                ft.Row(
                    [
                        order_type_badge(order_type),
                        status_badge(status_label, status_bg, status_text),
                    ],
                    spacing=6,

                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,

        )

        items_list = ft.Container(
            content=ft.Column([item_row(i[0], i[1]) for i in items], spacing=4),
            padding=ft.Padding.symmetric(vertical=12, horizontal=10),
            border=ft.Border.only(
                top=ft.BorderSide(1, COLORS["card_divider"]),
                bottom=ft.BorderSide(1, COLORS["card_divider"]),
            ),
        )

        delivery_info = None
        if order_type.lower() == "delivery":
            addr = (order.get("delivery") or {}).get("address", "")
            if addr:
                delivery_info = ft.Row(
                    [
                        ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=13,
                                color=COLORS["on_surface_variant"]),
                        ft.Text(addr, size=11, color=COLORS["on_surface_variant"],
                                weight=ft.FontWeight.W_500, expand=True),
                    ],
                    spacing=4,
                )

        footer = ft.Row(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.EDIT_OUTLINED, size=14, color=COLORS["primary"]),
                            ft.Text("Update Status", size=12,
                                    weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                        ],
                        spacing=4,
                    ),
                    bgcolor=COLORS["surface_container_low"],
                    padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                    border_radius=10,
                    border=ft.Border.all(1, COLORS["card_outline"]),
                    data=order,
                    on_click=on_tap,
                    ink=True,
                ),
                ft.Text(
                    f"Rs {order.get('total', '0.00')}",
                    size=16, weight=ft.FontWeight.W_800, color=COLORS["on_surface"],
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        col_children = [header, items_list]
        if delivery_info:
            col_children.append(
                ft.Container(content=delivery_info,
                             padding=ft.Padding.symmetric(vertical=6, horizontal=2))
            )
        col_children.append(footer)
        self.content = ft.Column(col_children, spacing=12)


def get_staff_orders_view(page: ft.Page):
    token = page.session.store.get("token")

    all_orders: list[dict] = []   # today's orders only, populated after fetch
    active_filter: list    = [None]
    chip_refs: dict        = {}

    cards_column           = ft.Column(controls=[loading_spinner()], spacing=16)
    summary_container      = ft.Container()


    def apply_filter():
        fval = active_filter[0]
        filtered = (
            all_orders if fval is None
            else [o for o in all_orders if o.get("order_type", "").lower() == fval]
        )
        cards_column.controls = (
            [StaffOrderCard(o, on_tap=open_status_sheet) for o in filtered]
            if filtered
            else [empty_state("No orders found for this filter.")]
        )
        page.update()

    def on_chip_click(e):
        label = e.control.data
        active_filter[0] = CHIP_FILTERS[label]
        for lbl, chip in chip_refs.items():
            is_active           = CHIP_FILTERS[lbl] == active_filter[0]
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
        order = e.control.data
        sheet = build_status_sheet(page, order, on_updated=reload_orders)
        page.overlay.append(sheet)
        sheet.open = True
        page.update()


    def build_summary_bar() -> ft.Container:
        total  = len(all_orders)
        active = sum(
            1 for o in all_orders
            if not is_order_done(o)
        )
        done = total - active

        def _stat(value: str, label: str) -> ft.Column:
            return ft.Column(
                [
                    ft.Text(value, size=22, weight=ft.FontWeight.W_800,
                            color=COLORS["primary"]),
                    ft.Text(label, size=10, color=COLORS["on_surface_variant"],
                            weight=ft.FontWeight.W_500),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            )

        def _div() -> ft.Container:
            return ft.Container(width=1, height=36, bgcolor=COLORS["card_divider"])

        return ft.Container(
            content=ft.Row(
                [_stat(str(total), "Total today"), _div(),
                 _stat(str(active), "Active"), _div(),
                 _stat(str(done), "Completed")],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor=COLORS["surface_container_lowest"],
            padding=ft.Padding.symmetric(vertical=14, horizontal=16),
            border_radius=16,
            border=ft.Border.all(1, COLORS["card_outline"]),
            shadow=ft.BoxShadow(
                offset=ft.Offset(0, 2), blur_radius=4, spread_radius=0,
                color=ft.Colors.with_opacity(0.15, COLORS["on_surface"]),
            ),
        )

    async def load_orders():
        data = await fetch_orders(token, staff=True)
        if data is None:
            cards_column.controls = [
                empty_state("Couldn't reach the server.\nCheck your connection.")
            ]
            page.update()
            return

        all_orders.clear()
        all_orders.extend(o for o in data if is_today(o.get("order_date", "")))

        summary_container.content = build_summary_bar()
        apply_filter()

    def reload_orders():
        page.run_task(load_orders)

    page.run_task(load_orders)

    main_content = ft.Column(
        [
            ft.Column(
                [
                    ft.Text("Orders", size=24, weight=ft.FontWeight.W_800,
                            color=COLORS["on_surface"]),
                    ft.Text("Manage today's orders",
                            size=14, color=COLORS["on_surface_variant"]),
                ],
                spacing=4,
            ),
            summary_container,
            render_chips(),
            ft.Divider(height=1, color=ft.Colors.TRANSPARENT),
            cards_column,
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Column(
        [
            ft.Container(
                content=main_content,
                padding=ft.Padding.only(left=24, right=24, top=16, bottom=24),
                expand=True,
            )
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def is_order_done(order: dict) -> bool:
    order_type = order.get("order_type", "").lower()
    if order_type == "dine in":
        return order.get("status", "") == "completed"
    if order_type == "delivery":
        return (order.get("delivery") or {}).get("delivery_status") == "delivered"
    if order_type == "pick up":
        return (order.get("takeout") or {}).get("pickup_status") == "picked_up"
    return False


if __name__ == "__main__":
    async def main(page: ft.Page):
        page.title   = "Escale - Staff Orders"
        page.bgcolor = COLORS["background"]
        page.padding = 0
        page.fonts   = {FONT_FAMILY: FONT_URL}
        page.theme   = build_theme()

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row([
                        ft.IconButton(ft.Icons.MENU, icon_color=COLORS["primary"]),
                        ft.Text("Escale", size=24, weight=ft.FontWeight.BOLD,
                                color=COLORS["on_surface"]),
                    ]),
                    ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON), radius=20),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.only(left=24, right=24, top=10, bottom=10),
            bgcolor=COLORS["background"],
        )

        page.add(ft.Column([header, get_staff_orders_view(page)], spacing=0, expand=True))

    ft.run(main)

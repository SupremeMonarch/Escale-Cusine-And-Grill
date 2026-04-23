import argparse
import json
import urllib.parse
import urllib.request

import flet as ft


TOPPING_PRICES = {
    "Eggs": 25,
    "Chicken": 0,
    "Shrimps": 30,
    "Beef": 15,
    "Lamb": 30,
    "Mushrooms": 20,
}
MEAT_TOPPINGS = ["Chicken", "Beef", "Lamb"]
EXTRA_TOPPINGS = ["Eggs", "Shrimps", "Mushrooms"]


def fetch_menu_data(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "ECAG-Flet-Client"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("categories", [])


def start_checkout(base_url: str, items: list[dict], order_type: str) -> str:
    endpoint = urllib.parse.urljoin(base_url, "/menu/mobile/checkout/start/")
    payload = {"items": items, "order_type": order_type}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ECAG-Flet-Client"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not parsed.get("ok"):
        raise RuntimeError(parsed.get("error", "Checkout start failed"))
    return parsed["checkout_url"]


def is_topping_eligible(name: str) -> bool:
    lowered = str(name or "").lower()
    return "fried rice" in lowered or "fried noodles" in lowered or "magic bowl" in lowered


def normalize_cart(items: list[dict]) -> list[dict]:
    normalized = []
    for item in items or []:
        if not item:
            continue
        entry = {
            "item_id": item.get("item_id"),
            "name": item.get("name", "Item"),
            "price": float(item.get("price", 0.0)),
            "quantity": max(1, int(item.get("quantity", 1))),
            "meat_topping": item.get("meat_topping", ""),
            "extra_toppings": item.get("extra_toppings", []),
        }
        if not isinstance(entry["extra_toppings"], list):
            entry["extra_toppings"] = []
        if is_topping_eligible(entry["name"]) and not entry["meat_topping"]:
            entry["meat_topping"] = "Chicken"
        normalized.append(entry)
    return normalized


def read_storage_json(page: ft.Page, key: str, fallback):
    try:
        raw = page.client_storage.get(key)
        if raw is None:
            return fallback
        if isinstance(raw, str):
            return json.loads(raw)
        return raw
    except Exception:
        return fallback


def write_storage_json(page: ft.Page, key: str, value) -> None:
    try:
        page.client_storage.set(key, json.dumps(value))
    except Exception:
        pass


def build_menu_card(item: dict, on_add) -> ft.Control:
    image_url = item.get("image_url")
    image_control = (
        ft.Image(src=image_url, width=84, height=84, fit=ft.ImageFit.COVER, border_radius=10)
        if image_url
        else ft.Container(width=84, height=84, bgcolor=ft.Colors.GREY_200, border_radius=10)
    )

    return ft.Container(
        margin=ft.margin.only(bottom=10),
        padding=10,
        border_radius=14,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
        content=ft.Row(
            spacing=10,
            controls=[
                image_control,
                ft.Expanded(
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Expanded(
                                        ft.Text(
                                            item.get("name", "Item"),
                                            size=14,
                                            weight=ft.FontWeight.W_700,
                                            color=ft.Colors.GREY_900,
                                        )
                                    ),
                                    ft.Text(
                                        f"Rs {item.get('price', '0.00')}",
                                        size=13,
                                        weight=ft.FontWeight.W_700,
                                        color=ft.Colors.AMBER_800,
                                    ),
                                ],
                            ),
                            ft.Text(
                                item.get("desc", ""),
                                size=12,
                                color=ft.Colors.GREY_600,
                                max_lines=3,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.END,
                                controls=[
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                        border_radius=8,
                                        bgcolor=ft.Colors.ORANGE_600,
                                        on_click=lambda e, item=item: on_add(item),
                                        content=ft.Text("Add", color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.W_700),
                                    )
                                ],
                            ),
                        ],
                    )
                ),
            ],
        ),
    )


def main(page: ft.Page):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-url", default="http://127.0.0.1:8000/menu/mobile/data/")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args, _ = parser.parse_known_args()

    page.title = "Escale Mobile Menu"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#FFF8F3"
    page.padding = 12
    page.window_width = 420
    page.window_height = 820
    page.window_resizable = True
    page.scroll = ft.ScrollMode.ADAPTIVE

    status = ft.Text("Loading menu...", color=ft.Colors.GREY_700)
    menu_content = ft.Column(spacing=10)
    cart_list = ft.Column(spacing=8)

    stored_cart = read_storage_json(page, "ecag_mobile_cart", [])
    cart_items = normalize_cart(stored_cart)

    stored_order_type = read_storage_json(page, "ecag_mobile_order_type", "dine_in")
    order_type_value = stored_order_type if stored_order_type in ["dine_in", "pick_up", "delivery"] else "dine_in"

    order_type_dd = ft.Dropdown(
        label="Order type",
        width=190,
        dense=True,
        value=order_type_value,
        options=[
            ft.dropdown.Option("dine_in", "Dine In"),
            ft.dropdown.Option("pick_up", "Pick Up"),
            ft.dropdown.Option("delivery", "Delivery"),
        ],
    )

    cart_count = ft.Text("0 items", color=ft.Colors.GREY_800)
    cart_total = ft.Text("Rs 0.00", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREY_900)

    def save_cart_state():
        write_storage_json(page, "ecag_mobile_cart", cart_items)
        write_storage_json(page, "ecag_mobile_order_type", order_type_dd.value or "dine_in")

    def cart_item_unit_price(item: dict) -> float:
        toppings_total = 0.0
        meat = item.get("meat_topping")
        if meat:
            toppings_total += TOPPING_PRICES.get(meat, 0)
        for topping in item.get("extra_toppings", []):
            toppings_total += TOPPING_PRICES.get(topping, 0)
        return float(item.get("price", 0.0)) + toppings_total

    def recalc_totals():
        count = 0
        subtotal = 0.0
        for item in cart_items:
            qty = int(item.get("quantity", 1))
            count += qty
            subtotal += qty * cart_item_unit_price(item)
        fee = 100.0 if order_type_dd.value == "delivery" else (50.0 if order_type_dd.value == "pick_up" else 0.0)
        total = subtotal + fee
        cart_count.value = f"{count} items"
        cart_total.value = f"Rs {total:.2f}"

    def set_meat(index: int, meat: str):
        if not (0 <= index < len(cart_items)):
            return
        cart_items[index]["meat_topping"] = meat
        save_cart_state()
        recalc_totals()
        render_cart()

    def toggle_extra(index: int, topping: str):
        if not (0 <= index < len(cart_items)):
            return
        extras = cart_items[index].setdefault("extra_toppings", [])
        if topping in extras:
            extras.remove(topping)
        else:
            extras.append(topping)
        save_cart_state()
        recalc_totals()
        render_cart()

    def update_qty(index: int, delta: int):
        if not (0 <= index < len(cart_items)):
            return
        cart_items[index]["quantity"] = int(cart_items[index].get("quantity", 1)) + delta
        if cart_items[index]["quantity"] <= 0:
            cart_items.pop(index)
        save_cart_state()
        recalc_totals()
        render_cart()

    def remove_item(index: int):
        if not (0 <= index < len(cart_items)):
            return
        cart_items.pop(index)
        save_cart_state()
        recalc_totals()
        render_cart()

    def render_cart():
        controls = []
        if not cart_items:
            controls.append(ft.Text("Cart is empty.", color=ft.Colors.GREY_500, size=12))
        else:
            for idx, item in enumerate(cart_items):
                unit = cart_item_unit_price(item)

                qty_controls = ft.Row(
                    spacing=6,
                    controls=[
                        ft.OutlinedButton("-", on_click=lambda e, i=idx: update_qty(i, -1), height=30),
                        ft.Text(str(item.get("quantity", 1)), width=24, text_align=ft.TextAlign.CENTER),
                        ft.OutlinedButton("+", on_click=lambda e, i=idx: update_qty(i, 1), height=30),
                        ft.TextButton("Remove", on_click=lambda e, i=idx: remove_item(i)),
                    ],
                )

                item_controls = [
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Expanded(ft.Text(item.get("name", "Item"), weight=ft.FontWeight.W_700, size=13)),
                            ft.Text(f"Rs {unit:.2f}", color=ft.Colors.AMBER_800, weight=ft.FontWeight.W_700, size=12),
                        ],
                    ),
                    qty_controls,
                ]

                if is_topping_eligible(item.get("name", "")):
                    item_controls.append(ft.Text("Meat", size=11, color=ft.Colors.GREY_700, weight=ft.FontWeight.W_700))
                    meat_chips = ft.Row(
                        wrap=True,
                        spacing=6,
                        controls=[
                            ft.FilterChip(
                                label=f"{meat} (+Rs {TOPPING_PRICES[meat]})" if TOPPING_PRICES[meat] else meat,
                                selected=(item.get("meat_topping") == meat),
                                on_select=lambda e, i=idx, m=meat: set_meat(i, m),
                            )
                            for meat in MEAT_TOPPINGS
                        ],
                    )
                    item_controls.append(meat_chips)

                    item_controls.append(ft.Text("Extras", size=11, color=ft.Colors.GREY_700, weight=ft.FontWeight.W_700))
                    extra_chips = ft.Row(
                        wrap=True,
                        spacing=6,
                        controls=[
                            ft.FilterChip(
                                label=f"{top} (+Rs {TOPPING_PRICES[top]})",
                                selected=(top in item.get("extra_toppings", [])),
                                on_select=lambda e, i=idx, t=top: toggle_extra(i, t),
                            )
                            for top in EXTRA_TOPPINGS
                        ],
                    )
                    item_controls.append(extra_chips)

                controls.append(
                    ft.Container(
                        padding=10,
                        border_radius=12,
                        bgcolor=ft.Colors.WHITE,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
                        content=ft.Column(spacing=6, controls=item_controls),
                    )
                )

        cart_list.controls = controls
        page.update()

    def add_to_cart(menu_item):
        item_id = menu_item.get("item_id")
        name = menu_item.get("name", "Item")
        price = float(menu_item.get("price", 0.0))
        default_meat = "Chicken" if is_topping_eligible(name) else ""

        existing = next(
            (
                x
                for x in cart_items
                if x.get("item_id") == item_id
                and x.get("price") == price
                and x.get("meat_topping", "") == default_meat
                and not x.get("extra_toppings")
            ),
            None,
        )

        if existing:
            existing["quantity"] = int(existing.get("quantity", 1)) + 1
        else:
            cart_items.append(
                {
                    "item_id": item_id,
                    "name": name,
                    "price": price,
                    "quantity": 1,
                    "meat_topping": default_meat,
                    "extra_toppings": [],
                }
            )

        status.value = f"Added: {name}"
        save_cart_state()
        recalc_totals()
        render_cart()

    def on_checkout(_):
        if not cart_items:
            status.value = "Cart is empty."
            page.update()
            return
        status.value = "Starting checkout..."
        page.update()
        try:
            payload = [
                {
                    "item_id": it.get("item_id"),
                    "quantity": it.get("quantity", 1),
                    "meat_topping": it.get("meat_topping", ""),
                    "extra_toppings": it.get("extra_toppings", []),
                }
                for it in cart_items
            ]
            checkout_link = start_checkout(args.base_url, payload, order_type_dd.value or "dine_in")
            page.launch_url(checkout_link)
            status.value = "Checkout opened in browser."
        except Exception as exc:
            status.value = f"Checkout failed: {exc}"
        page.update()

    def on_order_type_change(_):
        save_cart_state()
        recalc_totals()
        page.update()

    order_type_dd.on_change = on_order_type_change

    checkout_btn = ft.ElevatedButton(
        "Checkout",
        bgcolor=ft.Colors.AMBER_400,
        color=ft.Colors.GREY_900,
        on_click=on_checkout,
    )

    page.add(
        ft.Container(
            border_radius=18,
            padding=14,
            gradient=ft.LinearGradient(colors=["#FFB17A", "#EA580C", "#DC2626"]),
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text("Escale Mobile Menu", size=22, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                    ft.Text("Phone-first ordering view", color=ft.Colors.WHITE, size=13),
                ],
            ),
        ),
        status,
        ft.Row(controls=[order_type_dd]),
        menu_content,
        ft.Container(
            margin=ft.margin.only(top=8),
            padding=12,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(spacing=2, controls=[cart_count, cart_total]),
                            checkout_btn,
                        ],
                    ),
                    ft.Text("Cart details", size=12, weight=ft.FontWeight.W_700, color=ft.Colors.GREY_700),
                    cart_list,
                ],
            ),
        ),
    )

    try:
        categories = fetch_menu_data(args.data_url)
    except Exception as exc:
        status.value = f"Failed to load menu: {exc}"
        recalc_totals()
        render_cart()
        page.update()
        return

    if not categories:
        status.value = "No available items."
        recalc_totals()
        render_cart()
        page.update()
        return

    status.value = "Pick a category"

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=220,
        label_color=ft.Colors.WHITE,
        unselected_label_color=ft.Colors.GREY_700,
        indicator_color=ft.Colors.TRANSPARENT,
        divider_color=ft.Colors.TRANSPARENT,
        tabs=[],
    )

    for category in categories:
        category_controls = []
        for sub in category.get("subcategories", []):
            category_controls.append(
                ft.Text(
                    sub.get("subcategory", "Section").upper(),
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.ORANGE_800,
                )
            )
            category_controls.extend(build_menu_card(item, add_to_cart) for item in sub.get("items", []))

        tabs.tabs.append(
            ft.Tab(
                text=category.get("category", "Category"),
                content=ft.Container(
                    padding=ft.padding.only(top=8),
                    content=ft.Column(controls=category_controls, spacing=8, scroll=ft.ScrollMode.ADAPTIVE),
                ),
            )
        )

    menu_content.controls = [tabs]
    recalc_totals()
    render_cart()
    page.update()


if __name__ == "__main__":
    ft.app(target=main)

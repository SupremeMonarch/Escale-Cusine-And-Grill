from __future__ import annotations

import argparse
from collections.abc import Callable

import flet as ft

from .models import EXTRA_TOPPINGS, MEAT_TOPPINGS, TOPPING_PRICES, is_topping_eligible, normalize_cart
from .service import (
    complete_checkout,
    fetch_menu_data,
    read_storage_json,
    resolve_image_payload,
    start_checkout,
    write_storage_json,
)


def build_menu_card(item: dict, on_add, base_url: str = "http://127.0.0.1:8000") -> ft.Control:
    image_payload = resolve_image_payload(item.get("image_url", ""), base_url)
    fit_cover = ft.BoxFit.COVER if hasattr(ft, "BoxFit") else ft.ImageFit.COVER
    image_control = (
        ft.Image(width=84, height=84, fit=fit_cover, border_radius=10, **image_payload)
        if image_payload
        else ft.Container(width=84, height=84, bgcolor=ft.Colors.GREY_200, border_radius=10)
    )

    return ft.Container(
        margin=ft.Margin.only(bottom=10),
        padding=10,
        border_radius=14,
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
        content=ft.Row(
            spacing=10,
            controls=[
                image_control,
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Container(
                                        expand=True,
                                        content=ft.Text(
                                            item.get("name", "Item"),
                                            size=14,
                                            weight=ft.FontWeight.W_700,
                                            color=ft.Colors.GREY_900,
                                        ),
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
                                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                                        border_radius=8,
                                        bgcolor=ft.Colors.ORANGE_600,
                                        on_click=lambda e, item=item: on_add(item),
                                        content=ft.Text("Add", color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.W_700),
                                    )
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


class MenuFeature:
    def __init__(
        self,
        page: ft.Page,
        on_back: Callable[[], None] | None = None,
        data_url: str = "http://127.0.0.1:8000/menu/mobile/data/",
        base_url: str = "http://127.0.0.1:8000",
    ):
        self.page = page
        self.on_back = on_back
        self.data_url = data_url
        self.base_url = base_url

    def build_view(self) -> ft.Control:
        return build_menu_page(
            self.page,
            data_url=self.data_url,
            base_url=self.base_url,
            on_back=self.on_back,
            standalone=False,
        )


def build_menu_page(
    page: ft.Page,
    data_url: str = "http://127.0.0.1:8000/menu/mobile/data/",
    base_url: str = "http://127.0.0.1:8000",
    on_back=None,
    standalone: bool = False,
) -> ft.Control:
    if standalone:
        page.title = "Escale Mobile Menu"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = "#FFF8F3"
        page.padding = 12
        page.window_width = 420
        page.window_height = 820
        page.window_resizable = True
        page.scroll = ft.ScrollMode.ADAPTIVE
    else:
        if hasattr(page, "window_resizable"):
            page.window_resizable = True
        if hasattr(page, "window_min_width"):
            page.window_min_width = 360
        if hasattr(page, "window_min_height"):
            page.window_min_height = 640
        page.scroll = ft.ScrollMode.ADAPTIVE

    status = ft.Text("Loading menu...", color=ft.Colors.GREY_700)
    menu_content = ft.Column(spacing=10)
    cart_list = ft.Column(spacing=8)

    stored_cart = read_storage_json(page, "ecag_mobile_cart", [])
    cart_items = normalize_cart(stored_cart)

    stored_order_type = read_storage_json(page, "ecag_mobile_order_type", "dine_in")
    order_type_value = stored_order_type if stored_order_type in ["dine_in", "pick_up", "delivery"] else "dine_in"

    order_type_state = {"value": order_type_value}
    order_type_btns: list[tuple[ft.Button, str]] = []

    cart_count = ft.Text("0 items", color=ft.Colors.GREY_800)
    cart_total = ft.Text("Rs 0.00", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREY_900)

    def save_cart_state():
        write_storage_json(page, "ecag_mobile_cart", cart_items)
        write_storage_json(page, "ecag_mobile_order_type", order_type_state["value"])

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
        order_type = order_type_state["value"]
        fee = 100.0 if order_type == "delivery" else (50.0 if order_type == "pick_up" else 0.0)
        total = subtotal + fee
        cart_count.value = f"{count} items"
        cart_total.value = f"Rs {total:.2f}"

    def refresh_order_type_buttons():
        for btn, value in order_type_btns:
            selected = value == order_type_state["value"]
            btn.bgcolor = "#EA580C" if selected else "#F8FAFC"
            btn.color = ft.Colors.WHITE if selected else "#9A3412"
            btn.elevation = 0
            btn.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=999),
                side=ft.BorderSide(1, "#FDBA74" if selected else "#E5E7EB"),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            )

    def on_select_order_type(value: str):
        order_type_state["value"] = value
        save_cart_state()
        recalc_totals()
        refresh_order_type_buttons()
        if checkout_view.visible:
            address_section.visible = value == "delivery"
            if value == "delivery":
                refresh_address_options()
        page.update()

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
                            ft.Container(
                                expand=True,
                                content=ft.Text(item.get("name", "Item"), weight=ft.FontWeight.W_700, size=13),
                            ),
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
                            ft.ElevatedButton(
                                content=ft.Text(f"{meat} (+Rs {TOPPING_PRICES[meat]})" if TOPPING_PRICES[meat] else meat),
                                on_click=lambda e, i=idx, m=meat: set_meat(i, m),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.ORANGE_500 if item.get("meat_topping") == meat else ft.Colors.GREY_300,
                                    color=ft.Colors.WHITE if item.get("meat_topping") == meat else ft.Colors.BLACK,
                                ),
                                height=32,
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
                            ft.ElevatedButton(
                                content=ft.Text(f"{top} (+Rs {TOPPING_PRICES[top]})"),
                                on_click=lambda e, i=idx, t=top: toggle_extra(i, t),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.GREEN_500 if top in item.get("extra_toppings", []) else ft.Colors.GREY_300,
                                    color=ft.Colors.WHITE if top in item.get("extra_toppings", []) else ft.Colors.BLACK,
                                ),
                                height=32,
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
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
                        content=ft.Column(spacing=6, controls=item_controls),
                    )
                )

        cart_list.controls = controls
        page.update()

    def add_to_cart(menu_item):
        item_id = menu_item.get("item_id")
        name = menu_item.get("name", "Item")
        price = float(menu_item.get("price", 0.0))
        image_url = menu_item.get("image_url", "")
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
                    "image_url": image_url,
                    "quantity": 1,
                    "meat_topping": default_meat,
                    "extra_toppings": [],
                }
            )

        status.value = f"Added: {name}"
        save_cart_state()
        recalc_totals()
        render_cart()

    def order_type_label() -> str:
        return {
            "dine_in": "Dine In",
            "pick_up": "Pick Up",
            "delivery": "Delivery",
        }.get(order_type_state["value"], "Dine In")

    def build_checkout_payload() -> list[dict]:
        return [
            {
                "item_id": it.get("item_id"),
                "quantity": it.get("quantity", 1),
                "meat_topping": it.get("meat_topping", ""),
                "extra_toppings": it.get("extra_toppings", []),
            }
            for it in cart_items
        ]

    # Address selection for delivery
    stored_addresses = read_storage_json(page, "ecag_mobile_addresses", [])
    if not isinstance(stored_addresses, list):
        stored_addresses = []
    selected_address = {"value": ""}  # Will hold the selected address string
    address_error = ft.Text("", color=ft.Colors.RED_600, size=12)

    def load_default_address():
        profile_address = read_storage_json(page, "ecag_mobile_profile_address", "")
        if profile_address:
            selected_address["value"] = profile_address
        elif stored_addresses:
            selected_address["value"] = stored_addresses[0]

    load_default_address()

    address_options = ft.Column(spacing=8)
    address_input_fields = ft.Column(spacing=8, visible=False)
    new_address_street = ft.TextField(label="Street Address", dense=True, border_radius=10)
    new_address_city = ft.TextField(label="City", dense=True, border_radius=10)
    new_address_postal = ft.TextField(label="Postal Code", dense=True, border_radius=10)
    save_new_address_checkbox = ft.Checkbox(label="Save to profile", value=True)

    address_section = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
        visible=order_type_state["value"] == "delivery",
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text("Delivery Address", size=16, weight=ft.FontWeight.W_700),
                address_options,
                address_input_fields,
                address_error,
            ],
        ),
    )

    def refresh_address_options():
        controls = []
        if selected_address["value"]:
            controls.append(
                ft.Container(
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_50,
                    border=ft.Border.all(2, ft.Colors.BLUE_400),
                    content=ft.Text(f"Selected: {selected_address['value']}", size=14, color=ft.Colors.BLUE_900),
                )
            )
        controls.extend([
            ft.ElevatedButton(
                "Use Profile Address",
                on_click=lambda e: select_address(read_storage_json(page, "ecag_mobile_profile_address", "")),
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_500, color=ft.Colors.WHITE),
            ),
            ft.ElevatedButton(
                "Use Current Location",
                on_click=on_fetch_location,
                style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_500, color=ft.Colors.WHITE),
            ),
            ft.ElevatedButton(
                "Enter New Address",
                on_click=lambda e: show_address_form(),
                style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_500, color=ft.Colors.WHITE),
            ),
        ])
        address_options.controls = controls
        page.update()

    def select_address(addr: str):
        if addr:
            selected_address["value"] = addr
            address_error.value = ""
            address_input_fields.visible = False
            refresh_address_options()
        else:
            address_error.value = "No profile address found."

    async def fetch_location():
        try:
            # Request location permission
            await page.window.request_location_permission()
            location = await page.window.get_location_async()
            if location:
                # Reverse geocoding using Nominatim (OpenStreetMap)
                import urllib.request
                import json
                url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={location.latitude}&lon={location.longitude}&zoom=18&addressdetails=1"
                req = urllib.request.Request(url, headers={"User-Agent": "ECAG-Mobile-App"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    address = data.get("display_name", f"{location.latitude}, {location.longitude}")
                selected_address["value"] = address
                address_error.value = ""
                address_input_fields.visible = False
                refresh_address_options()
            else:
                address_error.value = "Unable to get location."
        except Exception as e:
            address_error.value = f"Location error: {e}"

    async def on_fetch_location(e):
        await fetch_location()

    def show_address_form():
        address_input_fields.visible = True
        page.update()

    def save_new_address():
        street = new_address_street.value or ""
        city = new_address_city.value or ""
        postal = new_address_postal.value or ""
        if not street or not city:
            address_error.value = "Street and City are required."
            return
        addr = f"{street}, {city}, {postal}".strip(", ")
        selected_address["value"] = addr
        if save_new_address_checkbox.value:
            write_storage_json(page, "ecag_mobile_profile_address", addr)
        address_error.value = ""
        address_input_fields.visible = False
        refresh_address_options()

    address_input_fields.controls = [
        new_address_street,
        new_address_city,
        new_address_postal,
        save_new_address_checkbox,
        ft.ElevatedButton("Save Address", on_click=lambda e: save_new_address()),
    ]

    refresh_address_options()

    checkout_status = ft.Text("", color=ft.Colors.GREY_700)
    checkout_items_column = ft.Column(spacing=8, height=280, scroll=ft.ScrollMode.ADAPTIVE)
    checkout_type_text = ft.Text("Dine In", size=12, color=ft.Colors.GREY_700)
    checkout_items_count_text = ft.Text("0", size=12, color=ft.Colors.GREY_700)
    checkout_fee_text = ft.Text("Rs 0.00", size=12, color=ft.Colors.GREY_700)
    checkout_subtotal_text = ft.Text("Rs 0.00", size=12, color=ft.Colors.GREY_700)
    checkout_total_text = ft.Text("Rs 0.00", size=22, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)

    payment_method_group = ft.RadioGroup(content=ft.Column(), value="card")
    card_name_input = ft.TextField(label="Name on Card", dense=True, border_radius=10)
    card_number_input = ft.TextField(label="Card Number", dense=True, border_radius=10)
    exp_date_input = ft.TextField(label="Expiration Date (YYYY-MM-DD)", dense=True, border_radius=10)
    cvv_input = ft.TextField(label="CVV", dense=True, border_radius=10, password=True, can_reveal_password=True)

    success_order_text = ft.Text("Order Confirmed", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)
    success_total_text = ft.Text("Rs 0.00", size=16, color="#FDBA74", weight=ft.FontWeight.W_600)

    menu_view = ft.Column(spacing=8)
    checkout_view = ft.Column(spacing=10, visible=False)
    success_view = ft.Column(spacing=10, visible=False)

    def refresh_card_fields():
        is_card = payment_method_group.value == "card"
        for field in [card_name_input, card_number_input, exp_date_input, cvv_input]:
            field.disabled = not is_card
            if not is_card:
                field.value = ""

    def render_checkout_items():
        controls = []
        items_count = 0
        subtotal = 0.0
        for item in cart_items:
            qty = int(item.get("quantity", 1))
            items_count += qty
            line_subtotal = qty * cart_item_unit_price(item)
            subtotal += line_subtotal

            image_payload = resolve_image_payload(item.get("image_url", ""), base_url)
            img = (
                ft.Image(width=48, height=48, border_radius=8, fit=ft.BoxFit.COVER, **image_payload)
                if image_payload
                else ft.Container(width=48, height=48, bgcolor=ft.Colors.GREY_300, border_radius=8)
            )

            toppings = []
            if item.get("meat_topping"):
                toppings.append(item.get("meat_topping"))
            toppings.extend(item.get("extra_toppings", []))

            controls.append(
                ft.Container(
                    padding=8,
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    img,
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text(item.get("name", "Item"), color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_600),
                                            ft.Text(f"Qty: {qty}", color="#D1D5DB", size=11),
                                            ft.Text(
                                                ", ".join(toppings) if toppings else "No toppings",
                                                color="#9CA3AF",
                                                size=10,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Text(f"Rs {line_subtotal:.2f}", color="#FDBA74", size=12, weight=ft.FontWeight.W_700),
                        ],
                    ),
                )
            )

        if not controls:
            controls = [ft.Text("Your cart is empty.", color="#9CA3AF", size=12)]

        fee = 100.0 if order_type_state["value"] == "delivery" else (50.0 if order_type_state["value"] == "pick_up" else 0.0)
        total = subtotal + fee

        checkout_items_column.controls = controls
        checkout_type_text.value = order_type_label()
        checkout_items_count_text.value = str(items_count)
        checkout_fee_text.value = f"Rs {fee:.2f}"
        checkout_subtotal_text.value = f"Rs {subtotal:.2f}"
        checkout_total_text.value = f"Rs {total:.2f}"

    def show_menu_view():
        menu_view.visible = True
        checkout_view.visible = False
        success_view.visible = False
        page.update()

    def show_checkout_view():
        render_checkout_items()
        checkout_status.value = ""
        address_error.value = ""
        address_section.visible = order_type_state["value"] == "delivery"
        if order_type_state["value"] == "delivery":
            refresh_address_options()
        menu_view.visible = False
        checkout_view.visible = True
        success_view.visible = False
        page.update()

    def show_success_view(order_code: str, total: str):
        success_order_text.value = f"Order {order_code or 'Confirmed'}"
        success_total_text.value = f"Total Paid: Rs {total}"
        menu_view.visible = False
        checkout_view.visible = False
        success_view.visible = True
        page.update()

    async def on_checkout(_):
        if not cart_items:
            status.value = "Cart is empty."
            page.update()
            return
        show_checkout_view()

    async def on_confirm_payment(_):
        if not cart_items:
            checkout_status.value = "Cart is empty."
            page.update()
            return

        if order_type_state["value"] == "delivery" and not selected_address["value"]:
            checkout_status.value = "Please select a delivery address."
            page.update()
            return

        if payment_method_group.value == "card":
            if not card_name_input.value or not card_number_input.value or not cvv_input.value:
                checkout_status.value = "Please fill card details."
                page.update()
                return

        checkout_status.value = "Processing payment..."
        page.update()

        try:
            payload = build_checkout_payload()
            address = selected_address["value"] if order_type_state["value"] == "delivery" else ""
            started = start_checkout(base_url, payload, order_type_state["value"], address)
            order_id = started.get("order_id")
            if not order_id:
                raise RuntimeError("Unable to start checkout")

            completed = complete_checkout(
                base_url,
                order_id=order_id,
                payment_method=payment_method_group.value or "card",
                card_name=card_name_input.value or "",
                card_number=card_number_input.value or "",
                exp_date=exp_date_input.value or "",
                cvv=cvv_input.value or "",
            )

            cart_items.clear()
            save_cart_state()
            recalc_totals()
            render_cart()
            show_success_view(completed.get("order_code", ""), completed.get("total", "0.00"))
        except Exception as exc:
            checkout_status.value = f"Checkout failed: {exc}"
            page.update()

            cart_items.clear()
            save_cart_state()
            recalc_totals()
            render_cart()
            show_success_view(completed.get("order_code", ""), completed.get("total", "0.00"))
        except Exception as exc:
            checkout_status.value = f"Checkout failed: {exc}"
            page.update()

    order_type_row = ft.Row(spacing=8, wrap=True)
    for value, label in [("dine_in", "Dine In"), ("pick_up", "Pick Up"), ("delivery", "Delivery")]:
        btn = ft.Button(
            content=label,
            on_click=lambda e, v=value: on_select_order_type(v),
            height=36,
            bgcolor="#F8FAFC",
            color="#9A3412",
        )
        order_type_btns.append((btn, value))
        order_type_row.controls.append(btn)

    refresh_order_type_buttons()

    checkout_btn = ft.Button(
        "Checkout",
        bgcolor=ft.Colors.AMBER_400,
        color=ft.Colors.GREY_900,
        on_click=on_checkout,
    )

    menu_header_controls = [
        ft.Container(
            border_radius=18,
            padding=14,
            gradient=ft.LinearGradient(colors=["#FFB17A", "#EA580C", "#DC2626"]),
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text("Escale Mobile Menu", size=22, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                    ft.Text("Fast ordering layout for phones", color=ft.Colors.WHITE, size=13),
                ],
            ),
        ),
    ]
    if on_back:
        menu_header_controls.append(ft.TextButton("Back", on_click=lambda e: on_back()))

    menu_view.controls = menu_header_controls + [
        status,
        order_type_row,
        menu_content,
        ft.Container(
            margin=ft.Margin.only(top=8),
            padding=12,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
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
    ]

    payment_method_group.content = ft.Column(
        spacing=6,
        controls=[
            ft.Radio(value="card", label="Credit Card"),
            ft.Radio(value="paypal", label="PayPal"),
            ft.Radio(value="juice", label="Juice"),
            ft.Radio(value="myt", label="My.T Mobile"),
        ],
    )
    payment_method_group.on_change = lambda e: (refresh_card_fields(), page.update())
    refresh_card_fields()

    checkout_view.controls = [
        ft.Container(
            border_radius=18,
            padding=14,
            gradient=ft.LinearGradient(colors=["#FFB17A", "#EA580C", "#DC2626"]),
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text("Checkout", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                    ft.Text("Review your order and pay", color=ft.Colors.WHITE, size=13),
                ],
            ),
        ),
        checkout_status,
        address_section,
        ft.Container(
            padding=12,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Payment Info", size=16, weight=ft.FontWeight.W_700),
                    payment_method_group,
                    card_name_input,
                    card_number_input,
                    exp_date_input,
                    cvv_input,
                ],
            ),
        ),
        ft.Container(
            padding=12,
            border_radius=14,
            bgcolor="#111827",
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("Your Order", size=16, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Order Type", color="#D1D5DB"), checkout_type_text]),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("No of Items", color="#D1D5DB"), checkout_items_count_text]),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Fee", color="#D1D5DB"), checkout_fee_text]),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Subtotal", color="#D1D5DB"), checkout_subtotal_text]),
                    ft.Divider(height=10, color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Total", color=ft.Colors.WHITE, weight=ft.FontWeight.W_700), checkout_total_text]),
                    checkout_items_column,
                ],
            ),
        ),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.OutlinedButton("Back", on_click=lambda e: show_menu_view()),
                ft.Button("Proceed to Payment", on_click=on_confirm_payment, bgcolor="#EA580C", color=ft.Colors.WHITE),
            ],
        ),
    ]

    success_view.controls = [
        ft.Container(
            border_radius=18,
            padding=18,
            gradient=ft.LinearGradient(colors=["#FFB17A", "#EA580C", "#DC2626"]),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Text("Payment Complete", size=28, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                    success_order_text,
                    success_total_text,
                    ft.Text("Thank You!", size=36, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Button("Order More", on_click=lambda e: show_menu_view(), bgcolor=ft.Colors.WHITE, color="#EA580C"),
                        ],
                    ),
                ],
            ),
        )
    ]

    root = ft.Container(
        expand=True,
        content=ft.Column(
            spacing=8,
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            controls=[menu_view, checkout_view, success_view],
        ),
    )

    try:
        categories = fetch_menu_data(data_url)
    except Exception as exc:
        status.value = f"Failed to load menu: {exc}"
        recalc_totals()
        render_cart()
        page.update()
        return root

    if not categories:
        status.value = "No available items."
        recalc_totals()
        render_cart()
        page.update()
        return root

    status.value = "Choose a category"

    selected_category = {"index": 0}
    category_btns: list[tuple[ft.Button, int]] = []
    category_tabs_row = ft.Row(spacing=8, wrap=False, scroll=ft.ScrollMode.ALWAYS)
    sections_column = ft.Column(spacing=8)

    def refresh_category_buttons():
        for btn, idx in category_btns:
            selected = idx == selected_category["index"]
            btn.bgcolor = "#EA580C" if selected else "#F3F4F6"
            btn.color = ft.Colors.WHITE if selected else "#1F2937"
            btn.elevation = 0
            btn.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=999),
                side=ft.BorderSide(1, "#FDBA74" if selected else "#E5E7EB"),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            )

    def render_selected_category():
        cat = categories[selected_category["index"]]
        controls = []
        for sub in cat.get("subcategories", []):
            controls.append(
                ft.Text(
                    sub.get("subcategory", "Section").upper(),
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color="#EA580C",
                )
            )
            controls.extend(build_menu_card(item, add_to_cart, base_url) for item in sub.get("items", []))
        sections_column.controls = controls

    def select_category(idx: int):
        selected_category["index"] = idx
        refresh_category_buttons()
        render_selected_category()
        page.update()

    for idx, category in enumerate(categories):
        btn = ft.Button(
            content=category.get("category", "Category"),
            on_click=lambda e, i=idx: select_category(i),
            height=38,
            bgcolor="#F3F4F6",
            color="#1F2937",
        )
        category_btns.append((btn, idx))
        category_tabs_row.controls.append(btn)

    refresh_category_buttons()
    render_selected_category()
    menu_content.controls = [category_tabs_row, sections_column]
    recalc_totals()
    render_cart()
    page.update()

    return root


def main(page: ft.Page):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-url", default="http://127.0.0.1:8000/menu/mobile/data/")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args, _ = parser.parse_known_args()

    page.add(
        build_menu_page(
            page,
            data_url=args.data_url,
            base_url=args.base_url,
            standalone=True,
        )
    )

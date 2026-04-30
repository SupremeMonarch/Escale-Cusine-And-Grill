from __future__ import annotations

import asyncio
import json
import os
from urllib import error, parse, request

import flet as ft
import requests


BASE_URL = os.getenv("ECAG_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_BASE = "/admin_panel/mobile"
ACTIVE_BASE_URL = BASE_URL


class ApiError(RuntimeError):
    pass


def _request_json(method: str, path: str, body: dict | None = None, query: dict | None = None, base_url: str | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    base = (base_url or ACTIVE_BASE_URL).rstrip("/")
    url = f"{base}{path}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"

    req = request.Request(url=url, headers=headers, data=data, method=method)

    try:
        with request.urlopen(req, timeout=12) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ApiError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
    except error.URLError as exc:
        raise ApiError(f"Cannot reach backend: {exc.reason}") from exc


def _request_multipart(method: str, path: str, data: dict, files: dict[str, str], base_url: str | None = None):
    base = (base_url or ACTIVE_BASE_URL).rstrip("/")
    url = f"{base}{path}"
    upload_files = {}
    try:
        for field_name, file_path in files.items():
            upload_files[field_name] = open(file_path, "rb")
        response = requests.request(method, url, data=data, files=upload_files, headers={"Accept": "application/json"}, timeout=20)
        if response.status_code >= 400:
            raise ApiError(f"HTTP {response.status_code}: {response.text or response.reason}")
        return response.json() if response.text else {}
    except requests.RequestException as exc:
        raise ApiError(f"Cannot reach backend: {exc}") from exc
    finally:
        for handle in upload_files.values():
            handle.close()


def _get_base_candidates() -> list[str]:
    candidates = [
        os.getenv("ECAG_API_BASE_URL", "").strip(),
        os.getenv("WEBSITE_BASE_URL", "").strip(),
        os.getenv("DJANGO_BASE_URL", "").strip(),
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        if not value:
            continue
        v = value.rstrip("/")
        if v in seen:
            continue
        seen.add(v)
        cleaned.append(v)
    return cleaned


def api_overview() -> dict:
    return _request_json("GET", f"{ADMIN_BASE}/overview/")


def api_orders(search: str = "", status: str = "all", order_type: str = "all") -> list[dict]:
    payload = _request_json("GET", f"{ADMIN_BASE}/orders/", query={"search": search, "status": status, "type": order_type})
    return payload.get("orders", [])


def api_order_action(order_id: int, action: str | None = None, status: str | None = None) -> None:
    body = {}
    if action:
        body["action"] = action
    if status:
        body["status"] = status
    _request_json("POST", f"{ADMIN_BASE}/orders/{order_id}/action/", body=body)


def api_reservations(query_text: str = "", status: str = "all") -> list[dict]:
    payload = _request_json("GET", f"{ADMIN_BASE}/reservations/", query={"q": query_text, "status": status})
    return payload.get("reservations", [])


def api_reservation_action(reservation_id: int, action: str | None = None, status: str | None = None) -> None:
    body = {}
    if action:
        body["action"] = action
    if status:
        body["status"] = status
    _request_json("POST", f"{ADMIN_BASE}/reservations/{reservation_id}/action/", body=body)


def api_menu(search: str = "", category: str = "") -> tuple[list[dict], list[dict]]:
    payload = _request_json("GET", f"{ADMIN_BASE}/menu/", query={"search": search, "category": category})
    return payload.get("menu_items", []), payload.get("categories", [])


def api_menu_action(item_id: int, action: str) -> None:
    _request_json("POST", f"{ADMIN_BASE}/menu/", body={"item_id": item_id, "action": action})


def api_menu_update(item_id: int, name: str, desc: str, price: str, subcategory_id: str, is_available: bool) -> None:
    _request_json(
        "POST",
        f"{ADMIN_BASE}/menu/",
        body={
            "item_id": item_id,
            "action": "edit",
            "name": name,
            "desc": desc,
            "price": price,
            "subcategory_id": subcategory_id,
            "is_available": is_available,
        },
    )


def api_menu_create(name: str, desc: str, price: str, subcategory_id: str, is_available: bool, image_path: str) -> None:
    _request_multipart(
        "POST",
        f"{ADMIN_BASE}/menu/",
        data={
            "action": "create",
            "name": name,
            "desc": desc,
            "price": price,
            "subcategory_id": subcategory_id,
            "is_available": str(is_available).lower(),
        },
        files={"menu_img": image_path},
    )


def api_customers(search: str = "") -> dict:
    return _request_json("GET", f"{ADMIN_BASE}/customers/", query={"search": search})


def api_staffs(search: str = "") -> dict:
    return _request_json("GET", f"{ADMIN_BASE}/staffs/", query={"search": search})


def api_staff_action(staff_id: int, action: str) -> dict:
    return _request_json("POST", f"{ADMIN_BASE}/staffs/", body={"staff_id": staff_id, "action": action})


def api_staff_action_with_data(staff_id: int, action: str, data: dict) -> dict:
    payload = {"staff_id": staff_id, "action": action}
    payload.update(data)
    return _request_json("POST", f"{ADMIN_BASE}/staffs/", body=payload)


def api_invite_staff(email: str, role: str) -> dict:
    return _request_json("POST", f"{ADMIN_BASE}/staffs/invite/", body={"email": email, "role": role})


def api_reviews(search: str = "", status: str = "all") -> tuple[list[dict], dict]:
    payload = _request_json("GET", f"{ADMIN_BASE}/reviews/", query={"search": search, "status": status})
    return payload.get("reviews", []), payload.get("stats", {})


def api_review_action(review_id: int, action: str, subject: str = "", message: str = "") -> None:
    body = {"action": action}
    if subject:
        body["subject"] = subject
    if message:
        body["message"] = message
    _request_json("POST", f"{ADMIN_BASE}/reviews/{review_id}/action/", body=body)


async def main(page: ft.Page):
    try:
        page.dialog = None
        page.overlay.clear()
    except Exception:
        pass

    page.title = "Escale Admin Mobile"
    page.bgcolor = "#f8fafc"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    accent = "#e97820"
    primary_btn = "#dc5e16"
    dark_btn = "#292626"
    text_dark = "#111827"
    text_muted = "#6b7280"
    card_bg = "#ffffff"
    chip_bg = "#f3f4f6"
    page_bg = "#f8fafc"
    line_color = "#e5e7eb"
    input_bg = "#f3f4f6"
    soft_orange = "#ffe4d3"

    content = ft.Container(expand=True)
    backend_status = ft.Text("Connecting to website...", size=11, color=text_muted)

    state = {
        "overview": {},
        "orders": [],
        "reservations": [],
        "menu_items": [],
        "menu_categories": [],
        "customers": [],
        "customer_stats": {},
        "staff": [],
        "staff_stats": {},
        "reviews": [],
        "review_stats": {},
    }

    ui = {
        "orders_search": "",
        "orders_filter": "all",
        "reservations_filter": "all",
        "menu_filter": "all",
        "menu_search": "",
        "customers_search": "",
        "customers_filter": "all",
        "staff_search": "",
        "staff_filter": "all",
        "staff_invite_email": "",
        "staff_invite_role": "staff",
        "reviews_filter": "all",
        "more_section": "customers",
    }

    def pad_sym(horizontal: int = 0, vertical: int = 0):
        if hasattr(ft, "Padding") and hasattr(ft.Padding, "symmetric"):
            return ft.Padding.symmetric(horizontal=horizontal, vertical=vertical)
        return ft.padding.symmetric(horizontal=horizontal, vertical=vertical)

    def elevated_btn(label: str, **kwargs):
        if hasattr(ft, "Button"):
            try:
                return ft.Button(text=label, **kwargs)
            except TypeError:
                return ft.Button(label, **kwargs)
        return ft.ElevatedButton(label, **kwargs)

    def show_toast(message: str, danger: bool = False):
        page.snack_bar = ft.SnackBar(content=ft.Text(message), open=True, bgcolor="#8b1e1e" if danger else "#2a2a2a")
        page.update()

    async def go_back_to_main_app(_=None):
        page.clean()
        page.navigation_bar = None
        page.bottom_appbar = None
        page.floating_action_button = None
        page.update()
        from main import main as main_app_shell

        main_app_shell(page)

    async def logout_to_main_app(_=None):
        try:
            page.session.store.set("token", "")
        except Exception:
            pass
        try:
            page.client_storage.remove("auth.token")
            page.client_storage.remove("auth.user")
        except Exception:
            pass
        await go_back_to_main_app()

    def card(child: ft.Control, padding: int = 14) -> ft.Control:
        return ft.Container(
            bgcolor=card_bg,
            border_radius=16,
            padding=padding,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.07, ft.Colors.BLACK)),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                offset=ft.Offset(0, 2),
                color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
            ),
            content=child,
        )

    def header_bar() -> ft.Control:
        return ft.Container(
            height=56,
            bgcolor="#f8f8f8",
            padding=pad_sym(horizontal=12, vertical=0),
            border=ft.Border.only(bottom=ft.BorderSide(1, "#e3e3e3")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.IconButton(icon=ft.Icons.MENU, icon_color="#FF5C00", on_click=lambda e: page.run_task(go_back_to_main_app, e)),
                            ft.Text("ESCALE CUISINE", size=16, weight=ft.FontWeight.BOLD, color="#FF5C00"),
                        ],
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.PERSON,
                        icon_color="#8a7765",
                        tooltip="Account",
                        items=[
                            ft.PopupMenuItem("Back to Main App", on_click=lambda e: page.run_task(go_back_to_main_app, e)),
                            ft.PopupMenuItem("Logout", on_click=lambda e: page.run_task(logout_to_main_app, e)),
                        ],
                    ),
                ],
            ),
        )

    def section_header(title: str, subtitle: str, tab_index: int) -> ft.Control:
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(title, size=21 if (page.width or 390) < 500 else 24, weight=ft.FontWeight.BOLD, color=text_dark, font_family="Georgia"),
                        ft.Text(subtitle, size=12, color=text_muted),
                    ],
                ),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=accent, on_click=lambda e: page.run_task(refresh_tab, tab_index)),
            ],
        )

    def chip_button(label: str, selected: bool, on_click):
        return ft.Container(
            border_radius=999,
            padding=pad_sym(horizontal=18, vertical=8),
            bgcolor=primary_btn if selected else chip_bg,
            content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color="#ffffff" if selected else "#374151"),
            on_click=on_click,
            ink=True,
        )

    def status_chip(value: str) -> ft.Control:
        s = (value or "-").lower().replace(" ", "_")
        cmap = {
            "completed": ("#d9f1e2", "#1f6b40"),
            "ready": ("#dff4e8", "#22a566"),
            "in_progress": ("#e5ecff", "#4f7ed6"),
            "preparing": ("#e5ecff", "#4f7ed6"),
            "pending": ("#faedd8", "#b3791a"),
            "confirmed": ("#ececec", "#5a5a5a"),
            "cancelled": ("#fbd8d8", "#8e2a2a"),
            "seated": ("#efe2ff", "#6e35b3"),
            "no_show": ("#f5d9dd", "#a13a51"),
            "active": ("#daf2e5", "#19885b"),
            "offline": ("#ececec", "#6f6f6f"),
            "on_shift": ("#daf2e5", "#19885b"),
            "vip": ("#fbe7d2", "#b85c00"),
            "regular": ("#ececec", "#6c6c6c"),
            "new": ("#d9f0df", "#1e9256"),
            "approved": ("#d9f1e2", "#1f6b40"),
        }
        bg, fg = cmap.get(s, ("#ececec", "#4a4a4a"))
        return ft.Container(
            padding=pad_sym(horizontal=10, vertical=4),
            border_radius=12,
            bgcolor=bg,
            content=ft.Text((value or "-").replace("_", " ").title(), color=fg, size=11, weight=ft.FontWeight.W_600),
        )

    def metric_card(title: str, value: str, hint: str, icon: str) -> ft.Control:
        return ft.Container(
            expand=True,
            bgcolor="#ffffff",
            border_radius=14,
            padding=12,
            border=ft.Border.all(1, line_color),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(title, size=12, color=text_muted), ft.Icon(icon, size=16, color=accent)]),
                    ft.Text(value, size=21, weight=ft.FontWeight.BOLD, color=text_dark),
                    ft.Text(hint, size=12, color=text_muted),
                ],
            ),
        )

    def _item_name(item: dict) -> str:
        if not item:
            return "Item"
        if isinstance(item, dict):
            return str(item.get("name") or item.get("title") or "Item")
        return str(item)

    def open_order_dialog(order: dict):
        items = order.get("items", []) or []
        user = order.get("user") or {}
        delivery = order.get("delivery") or {}
        order_type = str(order.get("order_type") or "-")

        # --- Items ---
        item_controls: list[ft.Control] = []
        for item in items:
            name = _item_name(item)
            qty = item.get("quantity", 1)
            price = item.get("price", "")
            subtotal = item.get("subtotal", "0.00")
            price_hint = f"Rs {price} each" if price and price != "0.00" else ""
            item_controls.append(
                ft.Container(
                    padding=pad_sym(horizontal=10, vertical=8),
                    border_radius=10,
                    bgcolor="#f9fafb",
                    content=ft.Column(spacing=2, controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(f"{qty}× {name}", size=13, weight=ft.FontWeight.W_600, color=text_dark, expand=True),
                                ft.Text(f"Rs {subtotal}", size=13, weight=ft.FontWeight.BOLD, color=text_dark),
                            ],
                        ),
                        *([ ft.Text(price_hint, size=11, color=text_muted) ] if price_hint else []),
                    ]),
                )
            )
        if not item_controls:
            item_controls.append(ft.Text("No items found.", size=12, color=text_muted))

        # --- Delivery section (only for delivery orders) ---
        delivery_controls: list[ft.Control] = []
        if order_type.lower() == "delivery" and delivery:
            delivery_controls = [
                ft.Divider(height=10, color=line_color),
                ft.Text("DELIVERY INFO", size=11, color=text_muted, weight=ft.FontWeight.W_600),
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=14, color=accent),
                    ft.Text(delivery.get("address") or "—", size=13, color=text_dark, expand=True),
                ]),
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.ACCESS_TIME_OUTLINED, size=14, color=accent),
                    ft.Text(f"ETA: {delivery.get('arrival_time') or '—'}", size=13, color=text_dark),
                ]),
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.LOCAL_SHIPPING_OUTLINED, size=14, color=accent),
                    ft.Text(f"Delivery fee: Rs {delivery.get('fee', '0.00')}", size=13, color=text_dark),
                ]),
            ]

        # --- Date formatting ---
        raw_date = order.get("order_date") or ""
        date_display = raw_date.replace("T", "  ")[:19] if raw_date else "—"

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(f"Order #{order.get('order_id_str') or order.get('id')}", weight=ft.FontWeight.BOLD, color=text_dark, size=16),
                    status_chip(order.get("status")),
                ],
            ),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=8,
                    controls=[
                        # Customer block
                        ft.Container(
                            bgcolor="#f9fafb", border_radius=10,
                            padding=pad_sym(horizontal=12, vertical=10),
                            content=ft.Column(spacing=4, controls=[
                                ft.Text("CUSTOMER", size=11, color=text_muted, weight=ft.FontWeight.W_600),
                                ft.Text(user.get("name") or "Guest", size=15, weight=ft.FontWeight.W_600, color=text_dark),
                                *([ ft.Row(spacing=4, controls=[ft.Icon(ft.Icons.EMAIL_OUTLINED, size=13, color=text_muted), ft.Text(user.get("email") or "—", size=12, color=text_muted)]) ] if user.get("email") else []),
                                *([ ft.Row(spacing=4, controls=[ft.Icon(ft.Icons.PHONE_OUTLINED, size=13, color=text_muted), ft.Text(user.get("phone") or "—", size=12, color=text_muted)]) ] if user.get("phone") else []),
                            ]),
                        ),
                        # Meta row
                        ft.Row(spacing=12, controls=[
                            ft.Row(spacing=4, controls=[ft.Icon(ft.Icons.CATEGORY_OUTLINED, size=13, color=accent), ft.Text(order_type.title(), size=12, color=text_dark)]),
                            ft.Row(spacing=4, controls=[ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, size=13, color=accent), ft.Text(date_display, size=12, color=text_dark)]),
                        ]),
                        ft.Divider(height=10, color=line_color),
                        ft.Text("ORDER ITEMS", size=11, color=text_muted, weight=ft.FontWeight.W_600),
                        *item_controls,
                        *delivery_controls,
                        ft.Divider(height=10, color=line_color),
                        # Totals
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Text("Subtotal", size=13, color=text_muted),
                            ft.Text(f"Rs {order.get('subtotal', order.get('total', '0.00'))}", size=13, color=text_dark),
                        ]),
                        *([ ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Text("Delivery fee", size=13, color=text_muted),
                            ft.Text(f"Rs {delivery.get('fee', '0.00')}", size=13, color=text_dark),
                        ]) ] if delivery else []),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Text("Total", size=15, weight=ft.FontWeight.BOLD, color=text_dark),
                            ft.Text(f"Rs {order.get('total', '0.00')}", size=16, weight=ft.FontWeight.W_800, color=accent),
                        ]),
                    ],
                ),
            ),
            actions=[ft.TextButton("Close", style=ft.ButtonStyle(color=text_dark), on_click=lambda e: _close_dialog(dlg))],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_customer_dialog(customer: dict):
        raw_last_order = customer.get("last_order_date") or ""
        last_order_display = raw_last_order.replace("T", "  ")[:19] if raw_last_order else "No completed orders yet"

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Customer Details", weight=ft.FontWeight.BOLD, color=text_dark, size=16),
                    status_chip(customer.get("status", "regular")),
                ],
            ),
            content=ft.Container(
                width=500,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=9,
                    controls=[
                        ft.Container(
                            bgcolor="#f9fafb",
                            border_radius=10,
                            padding=pad_sym(horizontal=12, vertical=10),
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(customer.get("name") or "Customer", size=16, weight=ft.FontWeight.W_600, color=text_dark),
                                    ft.Row(spacing=4, controls=[ft.Icon(ft.Icons.EMAIL_OUTLINED, size=13, color=text_muted), ft.Text(customer.get("email") or "—", size=12, color=text_muted)]),
                                ],
                            ),
                        ),
                        ft.Divider(height=10, color=line_color),
                        ft.Text("ORDER SUMMARY", size=11, color=text_muted, weight=ft.FontWeight.W_600),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Total orders", size=13, color=text_muted), ft.Text(str(customer.get("orders_count", 0)), size=13, color=text_dark, weight=ft.FontWeight.W_600)]),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Total spent", size=13, color=text_muted), ft.Text(f"Rs {float(str(customer.get('total_spent', 0) or 0)):.2f}", size=13, color=text_dark, weight=ft.FontWeight.W_600)]),
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, size=13, color=accent),
                                ft.Text(f"Last completed order: {last_order_display}", size=12, color=text_dark, expand=True),
                            ],
                        ),
                    ],
                ),
            ),
            actions=[ft.TextButton("Close", style=ft.ButtonStyle(color=text_dark), on_click=lambda e: _close_dialog(dlg))],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _close_dialog(dlg: ft.AlertDialog):
        dlg.open = False
        page.update()

    def open_temp_password_dialog(title: str, email: str, temporary_password: str, warning: str = ""):
        controls: list[ft.Control] = [
            ft.Text(f"Email: {email}", size=13, color=text_dark),
            ft.Text("Temporary Password", size=12, color=text_muted, weight=ft.FontWeight.W_600),
            ft.Container(
                padding=pad_sym(horizontal=12, vertical=10),
                border_radius=12,
                bgcolor=chip_bg,
                content=ft.Text(temporary_password, size=16, weight=ft.FontWeight.BOLD, color=text_dark),
            ),
            ft.Text("Share this securely and ask the staff member to change it after login.", size=12, color=text_muted),
        ]
        if warning:
            controls.append(ft.Text(warning, size=12, color="#b45309"))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD, color=text_dark),
            content=ft.Container(width=440, content=ft.Column(tight=True, spacing=10, controls=controls)),
            actions=[ft.TextButton("Close", style=ft.ButtonStyle(color=text_dark), on_click=lambda e: _close_dialog(dlg))],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    async def connect_backend() -> bool:
        global ACTIVE_BASE_URL
        for base in _get_base_candidates():
            try:
                await asyncio.to_thread(_request_json, "GET", f"{ADMIN_BASE}/overview/", None, None, base)
                ACTIVE_BASE_URL = base
                backend_status.value = f"Website data: {ACTIVE_BASE_URL}"
                backend_status.color = "#17623b"
                return True
            except Exception:
                continue
        backend_status.value = "Website data unavailable. Run Django server and verify /admin_panel/mobile endpoints."
        backend_status.color = "#8b1e1e"
        return False

    async def load_all():
        connected = await connect_backend()
        if not connected:
            page.update()
            return
        try:
            overview, orders, reservations, menu_data, customers, staffs, reviews_data = await asyncio.gather(
                asyncio.to_thread(api_overview),
                asyncio.to_thread(api_orders),
                asyncio.to_thread(api_reservations),
                asyncio.to_thread(api_menu),
                asyncio.to_thread(api_customers),
                asyncio.to_thread(api_staffs),
                asyncio.to_thread(api_reviews),
            )
            state["overview"] = overview
            state["orders"] = orders
            state["reservations"] = reservations
            state["menu_items"], state["menu_categories"] = menu_data
            state["customers"] = customers.get("customers", [])
            state["customer_stats"] = customers.get("stats", {})
            state["staff"] = staffs.get("staff_list", [])
            state["staff_stats"] = staffs.get("stats", {})
            state["reviews"] = reviews_data[0]
            state["review_stats"] = reviews_data[1]
        except Exception as exc:
            show_toast(f"Admin load failed: {exc}", danger=True)

    async def live_orders_poll():
        # Keep kitchen metrics current without requiring manual refresh.
        while True:
            await asyncio.sleep(5)
            try:
                state["orders"] = await asyncio.to_thread(api_orders)
                if int(page.navigation_bar.selected_index or 0) == 1:
                    render(1)
            except Exception:
                # Avoid noisy repeated error toasts during transient network issues.
                pass

    async def refresh_tab(index: int):
        try:
            if index == 0:
                state["overview"] = await asyncio.to_thread(api_overview)
            elif index == 1:
                state["orders"] = await asyncio.to_thread(api_orders)
            elif index == 2:
                state["reservations"] = await asyncio.to_thread(api_reservations)
            elif index == 3:
                state["menu_items"], state["menu_categories"] = await asyncio.to_thread(api_menu)
            elif index == 4:
                payload = await asyncio.to_thread(api_customers)
                state["customers"] = payload.get("customers", [])
                state["customer_stats"] = payload.get("stats", {})
            elif index == 5:
                payload = await asyncio.to_thread(api_staffs)
                state["staff"] = payload.get("staff_list", [])
                state["staff_stats"] = payload.get("stats", {})
            elif index == 6:
                reviews, stats = await asyncio.to_thread(api_reviews)
                state["reviews"] = reviews
                state["review_stats"] = stats
        except Exception as exc:
            show_toast(str(exc), danger=True)
        render(page.navigation_bar.selected_index)

    async def handle_order_set_status(order_id: int, status: str):
        try:
            await asyncio.to_thread(api_order_action, order_id, None, status)
            await refresh_tab(1)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_order_primary(order: dict):
        oid = int(order.get("id"))
        status = str(order.get("status") or "").lower()
        try:
            if status in ("in_progress", "preparing"):
                await asyncio.to_thread(api_order_action, oid, None, "ready")
            elif status == "ready":
                await asyncio.to_thread(api_order_action, oid, None, "completed")
            else:
                await asyncio.to_thread(api_order_action, oid, "next", None)
            await refresh_tab(1)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_order_cancel(order_id: int):
        try:
            await asyncio.to_thread(api_order_action, order_id, "cancel", None)
            await refresh_tab(1)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_reservation_set_status(reservation_id: int, status: str):
        try:
            await asyncio.to_thread(api_reservation_action, reservation_id, None, status)
            await refresh_tab(2)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_menu_toggle(item_id: int):
        try:
            await asyncio.to_thread(api_menu_action, item_id, "toggle_availability")
            await refresh_tab(3)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_menu_delete(item_id: int):
        try:
            await asyncio.to_thread(api_menu_action, item_id, "delete")
            await refresh_tab(3)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_menu_update(item_id: int, name: str, desc: str, price: str, subcategory_id: str, is_available: bool) -> bool:
        try:
            await asyncio.to_thread(api_menu_update, item_id, name, desc, price, subcategory_id, is_available)
            show_toast("Menu item updated.")
            await refresh_tab(3)
            return True
        except Exception as exc:
            show_toast(str(exc), danger=True)
            return False

    async def handle_menu_create(name: str, desc: str, price: str, subcategory_id: str, is_available: bool, image_path: str) -> bool:
        try:
            await asyncio.to_thread(api_menu_create, name, desc, price, subcategory_id, is_available, image_path)
            show_toast("Menu item added.")
            await refresh_tab(3)
            return True
        except Exception as exc:
            show_toast(str(exc), danger=True)
            return False

    async def handle_staff_action(staff_id: int, action: str):
        try:
            result = await asyncio.to_thread(api_staff_action, staff_id, action)
            if action == "reset_password" and isinstance(result, dict):
                email = str(result.get("email") or "").strip()
                temporary_password = str(result.get("temporary_password") or "").strip()
                warning = str(result.get("warning") or "").strip()
                if temporary_password:
                    open_temp_password_dialog("Temporary Password Reset", email, temporary_password, warning)
                else:
                    show_toast("Password reset completed.")
            await refresh_tab(5)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_invite_staff(email: str, role: str):
        email = (email or "").strip()
        role = (role or "staff").strip().lower()
        if not email:
            show_toast("Enter an email first.", danger=True)
            return
        if "@" not in email:
            show_toast("Enter a valid email address.", danger=True)
            return
        try:
            result = await asyncio.to_thread(api_invite_staff, email, role)
            temporary_password = str((result or {}).get("temporary_password") or "").strip()
            warning = str((result or {}).get("warning") or "").strip()
            if temporary_password:
                open_temp_password_dialog("Temporary Password Created", email, temporary_password, warning)
            else:
                show_toast(f"Invite sent to {email}.")
            ui["staff_invite_email"] = ""
            ui["staff_invite_role"] = "staff"
            await refresh_tab(5)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    def open_staff_edit_dialog(staff: dict):
        staff_id = int(staff.get("id"))
        current_role = "admin" if bool(staff.get("is_admin")) else "staff"
        current_username = str(staff.get("username") or "").strip()
        
        role_field = ft.Dropdown(
            label="Role",
            value=current_role,
            options=[ft.dropdown.Option("staff"), ft.dropdown.Option("admin")],
        )
        username_field = ft.TextField(
            label="Username",
            value=current_username,
        )

        async def _save(_):
            new_role = str(role_field.value or current_role).strip().lower()
            new_username = str(username_field.value or "").strip()
            role_changed = new_role != current_role
            username_changed = new_username != current_username
            
            if not role_changed and not username_changed:
                show_toast("No changes to save.")
                _close_dialog(dlg)
                return

            try:
                if username_changed:
                    if not new_username:
                        show_toast("Username cannot be empty.", danger=True)
                        return
                    await asyncio.to_thread(api_staff_action_with_data, staff_id, "update_username", {"username": new_username})
                    show_toast(f"Username updated to {new_username}.")
                
                if role_changed:
                    action = "make_admin" if new_role == "admin" else "make_staff"
                    await asyncio.to_thread(api_staff_action, staff_id, action)
                    show_toast(f"Role updated to {new_role}.")
                
                _close_dialog(dlg)
                await refresh_tab(5)
            except Exception as exc:
                show_toast(str(exc), danger=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Staff", weight=ft.FontWeight.BOLD, color=text_dark),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text(str(staff.get("name") or "Staff"), size=16, weight=ft.FontWeight.W_600, color=text_dark),
                        ft.Text(str(staff.get("email") or ""), size=12, color=text_muted),
                        username_field,
                        role_field,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color=text_dark), on_click=lambda e: _close_dialog(dlg)),
                elevated_btn("Save", style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff"), on_click=lambda e: page.run_task(_save, e)),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    async def handle_review_action(review_id: int, action: str):
        try:
            await asyncio.to_thread(api_review_action, review_id, action)
            await refresh_tab(6)
        except Exception as exc:
            show_toast(str(exc), danger=True)

    async def handle_email_response(review: dict, subject: str, message: str):
        rid = int(review.get("review_id"))
        try:
            await asyncio.to_thread(api_review_action, rid, "email_response", subject, message)
            show_toast("Response email sent.")
        except Exception as exc:
            show_toast(str(exc), danger=True)

    def open_email_dialog(review: dict):
        subject = ft.TextField(label="Subject", value="Response to your review")
        message = ft.TextField(label="Message", multiline=True, min_lines=4, max_lines=6)

        async def _send(_):
            await handle_email_response(review, subject.value or "", message.value or "")
            _close_dialog(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Email Response", weight=ft.FontWeight.BOLD),
            content=ft.Column(tight=True, controls=[subject, message]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close_dialog(dlg)),
                elevated_btn("Send", style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff"), on_click=lambda e: page.run_task(_send, e)),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_menu_edit_dialog(item: dict):
        category_options = [
            ft.dropdown.Option(str(c.get("subcategory_id")), str(c.get("subcategory") or "Category"))
            for c in state.get("menu_categories", [])
            if c.get("subcategory_id")
        ]
        name_field = ft.TextField(label="Item name", value=str(item.get("name") or ""))
        desc_field = ft.TextField(label="Description", value=str(item.get("desc") or ""), multiline=True, min_lines=3, max_lines=4)
        price_field = ft.TextField(label="Price (Rs)", value=str(item.get("price") or "0.00"), keyboard_type=ft.KeyboardType.NUMBER)
        category_field = ft.Dropdown(
            label="Category",
            value=str(item.get("subcategory_id") or ""),
            options=category_options,
        )
        availability_field = ft.Dropdown(
            label="Availability",
            value="true" if item.get("is_available") else "false",
            options=[
                ft.dropdown.Option("true", "Available"),
                ft.dropdown.Option("false", "Unavailable"),
            ],
        )

        async def _save(_):
            success = await handle_menu_update(
                int(item.get("item_id")),
                (name_field.value or "").strip(),
                (desc_field.value or "").strip(),
                (price_field.value or "").strip(),
                str(category_field.value or "").strip(),
                str(availability_field.value or "false").lower() == "true",
            )
            if success:
                _close_dialog(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Edit {item.get('name', 'Menu Item')}", weight=ft.FontWeight.BOLD, color=text_dark),
            content=ft.Container(
                width=460,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[name_field, desc_field, price_field, category_field, availability_field],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color=text_dark), on_click=lambda e: _close_dialog(dlg)),
                elevated_btn("Save", style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff"), on_click=lambda e: page.run_task(_save, e)),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_menu_create_dialog():
        category_options = [
            ft.dropdown.Option(str(c.get("subcategory_id")), str(c.get("subcategory") or "Category"))
            for c in state.get("menu_categories", [])
            if c.get("subcategory_id")
        ]
        selected_image = {"path": ""}
        name_field = ft.TextField(label="Item name")
        desc_field = ft.TextField(label="Description", multiline=True, min_lines=3, max_lines=4)
        price_field = ft.TextField(label="Price (Rs)", value="0.00", keyboard_type=ft.KeyboardType.NUMBER)
        category_field = ft.Dropdown(label="Category", options=category_options, value=str((state.get("menu_categories") or [{}])[0].get("subcategory_id") or "") if state.get("menu_categories") else "")
        availability_field = ft.Dropdown(
            label="Availability",
            value="true",
            options=[
                ft.dropdown.Option("true", "Available"),
                ft.dropdown.Option("false", "Unavailable"),
            ],
        )
        image_path_field = ft.TextField(label="Image file path", hint_text="C:/.../menu_image.jpg")
        image_label = ft.Text("No image selected", size=12, color=text_muted)

        async def _save(_):
            selected_image["path"] = (image_path_field.value or "").strip() or selected_image["path"]
            if not selected_image["path"]:
                show_toast("Select an image or enter its file path.", danger=True)
                return
            success = await handle_menu_create(
                (name_field.value or "").strip(),
                (desc_field.value or "").strip(),
                (price_field.value or "").strip(),
                str(category_field.value or "").strip(),
                str(availability_field.value or "false").lower() == "true",
                selected_image["path"],
            )
            if success:
                _close_dialog(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add Menu Item", weight=ft.FontWeight.BOLD, color=text_dark),
            content=ft.Container(
                width=460,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        name_field,
                        desc_field,
                        price_field,
                        category_field,
                        availability_field,
                        image_path_field,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                image_label,
                                ft.Text("Use image file path above", size=11, color=text_muted),
                            ],
                        ),
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color=text_dark), on_click=lambda e: _close_dialog(dlg)),
                elevated_btn("Add Item", style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff"), on_click=lambda e: page.run_task(_save, e)),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def order_primary_label(status: str) -> str:
        s = (status or "").lower()
        if s == "pending":
            return "Confirm"
        if s == "confirmed":
            return "Prepare"
        if s in ("in_progress", "preparing"):
            return "Mark Ready"
        if s == "ready":
            return "Complete"
        return "Next"

    def weekly_revenue_chart(labels: list[str], values: list[float]) -> ft.Control:
        labels = labels or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        values = values or [0.0] * len(labels)

        if len(values) < len(labels):
            values = values + [0.0] * (len(labels) - len(values))

        max_val = max(values) if values else 0.0
        max_val = max(max_val, 1.0)

        if hasattr(ft, "BarChart") and hasattr(ft, "BarChartGroup") and hasattr(ft, "BarChartRod"):
            return ft.BarChart(
                expand=True,
                bar_groups=[
                    ft.BarChartGroup(
                        x=i,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0,
                                to_y=max(values[i], 0.01),
                                width=22,
                                color=accent,
                                border_radius=ft.BorderRadius(top_left=4, top_right=4, bottom_left=0, bottom_right=0),
                            )
                        ],
                    )
                    for i in range(len(labels))
                ],
                bottom_axis=ft.ChartAxis(
                    labels=[
                        ft.ChartAxisLabel(value=i, label=ft.Text(labels[i], size=10, color=text_muted))
                        for i in range(len(labels))
                    ],
                    labels_size=22,
                ),
                left_axis=ft.ChartAxis(labels_size=0),
                horizontal_grid_lines=ft.ChartGridLines(color=line_color, width=1, dash_pattern=[4, 4]),
                max_y=max_val * 1.25,
                interactive=True,
                tooltip_bgcolor=soft_orange,
            )

        # Fallback for older Flet versions without chart controls.
        bar_columns: list[ft.Control] = []
        for i, lbl in enumerate(labels):
            raw = float(values[i]) if i < len(values) else 0.0
            ratio = raw / max_val
            bar_height = 12 + int(92 * ratio)
            bar_columns.append(
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Text(f"{raw:,.0f}", size=9, color=text_muted),
                        ft.Container(
                            width=20,
                            height=bar_height,
                            border_radius=ft.border_radius.only(top_left=4, top_right=4),
                            bgcolor=accent,
                        ),
                        ft.Text(lbl, size=10, color=text_muted),
                    ],
                )
            )

        return ft.Container(
            alignment=ft.Alignment(0, 1),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=bar_columns,
            ),
        )

    def _avatar(name: str) -> ft.Control:
        initials = "".join([p[0] for p in name.split()[:2]]).upper() if name else "NA"
        return ft.Container(
            width=42,
            height=42,
            border_radius=12,
            bgcolor=soft_orange,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(initials, weight=ft.FontWeight.BOLD, color=primary_btn),
        )

    def build_overview() -> ft.Control:
        metrics = state["overview"].get("metrics", {})
        recent_orders = state["overview"].get("recent_orders", [])[:4]
        chart_labels: list[str] = state["overview"].get("chart_labels", ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        chart_data: list[float] = state["overview"].get("chart_data", [0,0,0,0,0,0,0])

        activity_controls: list[ft.Control] = []
        for o in recent_orders:
            activity_controls.append(
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(width=28, height=28, border_radius=14, bgcolor=soft_orange, alignment=ft.Alignment(0, 0), content=ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, size=14, color=accent)),
                        ft.Column(expand=True, spacing=1, controls=[
                            ft.Text(f"New Order #{o.get('order_id_str') or o.get('id')}", size=13, weight=ft.FontWeight.W_600, color=text_dark),
                            ft.Text((o.get("order_type") or "-").title(), size=12, color=text_muted),
                        ]),
                        status_chip(o.get("status")),
                    ],
                )
            )

        if not activity_controls:
            activity_controls = [ft.Text("No recent activity.", size=12, color=text_muted)]

        return ft.Container(
            expand=True,
            bgcolor=page_bg,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    header_bar(),
                    ft.Container(
                        expand=True,
                        padding=14,
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            spacing=12,
                            controls=[
                                backend_status,
                                ft.Row(spacing=10, controls=[
                                    metric_card("REVENUE", f"Rs {metrics.get('total_revenue', '0.00')}", "+12% vs last week", ft.Icons.PAYMENTS_OUTLINED),
                                    metric_card("ACTIVE ORDERS", str(metrics.get('active_orders', 0)), "Kitchen queue", ft.Icons.RECEIPT_LONG_OUTLINED),
                                ]),
                                ft.Row(spacing=10, controls=[
                                    metric_card("RESERVATIONS", str(metrics.get('pending_reservations', 0)), "Pending approval", ft.Icons.EVENT_SEAT_OUTLINED),
                                    metric_card("CUSTOMERS", str(metrics.get('total_customers', 0)), "Total profiles", ft.Icons.GROUPS_OUTLINED),
                                ]),
                                card(ft.Column(spacing=8, controls=[
                                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                                        ft.Column(spacing=1, controls=[
                                            ft.Text("Weekly Performance", size=16, weight=ft.FontWeight.BOLD, color=text_dark, font_family="Georgia"),
                                            ft.Text("Revenue growth across the last 7 days", size=12, color=text_muted),
                                        ]),
                                        ft.Container(padding=pad_sym(horizontal=12, vertical=8), border_radius=10, bgcolor=input_bg, content=ft.Text("Last 7 Days", color=text_muted)),
                                    ]),
                                    ft.Container(
                                        height=170,
                                        border_radius=12,
                                        bgcolor="#ffffff",
                                        padding=ft.Padding(left=8, right=8, top=8, bottom=4),
                                        content=weekly_revenue_chart(chart_labels, chart_data),
                                    ),
                                ])),
                                card(ft.Column(spacing=10, controls=[
                                    ft.Text("Recent Activity", size=16, weight=ft.FontWeight.BOLD, color=text_dark, font_family="Georgia"),
                                    *activity_controls,
                                    elevated_btn("VIEW ALL ACTIVITY", style=ft.ButtonStyle(bgcolor="#ffffff", color=accent, shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, line_color),), on_click=lambda e: go_to_orders()),
                                ])),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def build_orders() -> ft.Control:
        search = ui["orders_search"].strip().lower()
        selected = ui["orders_filter"]

        orders = state["orders"]
        if search:
            orders = [
                o for o in orders
                if search in str(o.get("order_id_str", "")).lower()
                or search in str((o.get("user") or {}).get("name", "")).lower()
            ]
        if selected == "pending":
            orders = [o for o in orders if str(o.get("status", "")).lower() == "pending"]
        elif selected == "preparing":
            orders = [o for o in orders if str(o.get("status", "")).lower() in ("in_progress", "preparing")]

        active_count = sum(1 for o in state["orders"] if str(o.get("status", "")).lower() in ("pending", "confirmed", "in_progress", "preparing"))
        preparing_count = sum(1 for o in state["orders"] if str(o.get("status", "")).lower() in ("in_progress", "preparing"))
        total_revenue = sum(float(str(o.get("total", 0) or 0)) for o in state["orders"] if str(o.get("status", "")).lower() == "completed")

        cards: list[ft.Control] = []
        for o in orders:
            oid = int(o.get("id"))
            status = str(o.get("status") or "-")
            items_text = ", ".join([f"{i.get('quantity', 1)}x {_item_name(i)}" for i in (o.get("items") or [])[:2]]) or "No items"
            cards.append(
                card(ft.Column(spacing=8, controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text(f"#{o.get('order_id_str') or oid}", size=16, weight=ft.FontWeight.W_700, color=text_muted),
                        status_chip(status),
                    ]),
                    ft.Text((o.get("user") or {}).get("name") or "Guest", size=18, weight=ft.FontWeight.W_600, color=text_dark, font_family="Georgia"),
                    ft.Divider(height=6, color=line_color),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text(items_text, size=13, color=text_muted, expand=True),
                        ft.Text(f"Rs {float(str(o.get('total', 0) or 0)):.2f}", size=16, color=text_dark),
                    ]),
                    ft.Row(spacing=8, controls=[
                        *([] if status.lower() in ("completed", "cancelled") else [
                            elevated_btn(
                                order_primary_label(status),
                                style=ft.ButtonStyle(bgcolor=dark_btn if status.lower() == "ready" else primary_btn, color="#ffffff", shape=ft.RoundedRectangleBorder(radius=10)),
                                width=138,
                                on_click=lambda e, order=o: page.run_task(handle_order_primary, order),
                            ),
                        ]),
                        ft.OutlinedButton("View", width=86, on_click=lambda e, order=o: open_order_dialog(order)),
                    ]),
                ]))
            )

        return ft.Container(
            expand=True,
            bgcolor=page_bg,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    header_bar(),
                    ft.Container(
                        expand=True,
                        padding=14,
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            spacing=12,
                            controls=[
                                card(ft.Column(spacing=10, controls=[
                                    ft.Text("LIVE STATUS", size=12, color=text_muted),
                                    ft.Text("Kitchen Overview", size=20, weight=ft.FontWeight.BOLD, color=text_dark, font_family="Georgia"),
                                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[
                                        ft.Column(spacing=0, controls=[ft.Text(str(active_count), size=42, color=accent, weight=ft.FontWeight.BOLD), ft.Text("Active Orders", color=text_muted)]),
                                        ft.VerticalDivider(width=1, color=line_color),
                                        ft.Column(spacing=0, controls=[ft.Text(f"{preparing_count:02d}", size=42, color=text_dark, weight=ft.FontWeight.BOLD), ft.Text("Preparing", color=text_muted)]),
                                    ]),
                                ])),
                                ft.Container(
                                    border_radius=14,
                                    bgcolor=primary_btn,
                                    padding=14,
                                    content=ft.Column(spacing=2, controls=[
                                        ft.Text("Daily Revenue", color="#fff1e6"),
                                        ft.Text(f"Rs {total_revenue:,.0f}", size=32, color="#ffffff", weight=ft.FontWeight.BOLD, font_family="Georgia"),
                                    ]),
                                ),
                                ft.TextField(prefix_icon=ft.Icons.SEARCH, hint_text="Search Order ID, Customer...", value=ui["orders_search"], on_change=lambda e: _set_ui("orders_search", e.control.value), border_radius=16, bgcolor=input_bg, border_color=input_bg),
                                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                                    chip_button("All Orders", selected == "all", lambda e: _set_ui("orders_filter", "all")),
                                    chip_button("Pending", selected == "pending", lambda e: _set_ui("orders_filter", "pending")),
                                    chip_button("Preparing", selected == "preparing", lambda e: _set_ui("orders_filter", "preparing")),
                                ]),
                                *(cards if cards else [ft.Text("No orders found.", color=text_muted)]),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def build_reservations() -> ft.Control:
        selected = ui["reservations_filter"]
        reservations = state["reservations"]
        if selected != "all":
            reservations = [r for r in reservations if str(r.get("status", "")).lower() == selected]

        cards: list[ft.Control] = []
        for r in reservations:
            rid = int(r.get("reservation_id"))
            status = str(r.get("status") or "-")
            date_txt = (r.get("date") or "").replace("T", " ")
            time_txt = str(r.get("time") or "")[:5]
            table = (r.get("table") or {}).get("table_number")
            cards.append(
                card(ft.Column(spacing=8, controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[status_chip(status), ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END, controls=[ft.Text("Tonight" if status == "pending" else date_txt, color=accent if status == "pending" else text_dark, weight=ft.FontWeight.W_600), ft.Text(time_txt or "-", color=text_dark)])]),
                    ft.Text(r.get("full_name") or "Guest", size=20, weight=ft.FontWeight.W_600, color=text_dark, font_family="Georgia"),
                    ft.Divider(height=6, color=line_color),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(f"{r.get('guest_count', '-')} Guests", color=text_dark), ft.Text(f"Table {table}" if table else "Unassigned", color=text_dark)]),
                    ft.Row(visible=status == "pending", spacing=8, controls=[
                        elevated_btn("Confirm", expand=True, style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff"), on_click=lambda e, id_=rid: page.run_task(handle_reservation_set_status, id_, "confirmed")),
                        ft.OutlinedButton("Cancel", expand=True, on_click=lambda e, id_=rid: page.run_task(handle_reservation_set_status, id_, "cancelled")),
                    ]),
                ]))
            )

        return ft.Container(expand=True, bgcolor=page_bg, content=ft.Column(expand=True, spacing=0, controls=[
            header_bar(),
            ft.Container(expand=True, padding=14, content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=12, controls=[
                section_header("Reservations", "Manage your upcoming guest sittings and floor plan.", 2),
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    chip_button("All", selected == "all", lambda e: _set_ui("reservations_filter", "all")),
                    chip_button("Pending", selected == "pending", lambda e: _set_ui("reservations_filter", "pending")),
                    chip_button("Confirmed", selected == "confirmed", lambda e: _set_ui("reservations_filter", "confirmed")),
                ]),
                *(cards if cards else [ft.Text("No reservations found.", color=text_muted)]),
            ])),
        ]))

    def build_menu() -> ft.Control:
        selected = str(ui["menu_filter"]).lower()
        search = str(ui.get("menu_search", "")).strip().lower()
        items = state["menu_items"]
        if search:
            items = [
                i for i in items
                if search in str(i.get("name", "")).lower()
                or search in str(i.get("desc", "")).lower()
            ]
        if selected != "all":
            items = [i for i in items if str((i.get("subcategory") or "")).lower() == selected]

        categories = ["all"] + [str(c.get("subcategory", "")).strip() for c in state["menu_categories"] if c.get("subcategory")]
        categories_unique = []
        for c in categories:
            if c and c.lower() not in [x.lower() for x in categories_unique]:
                categories_unique.append(c)

        screen_w = page.width or 390
        tile_width = 280 if screen_w >= 980 else 240 if screen_w >= 700 else 210 if screen_w >= 520 else max(160, (screen_w - 44) / 2)
        cols = 4

        cards: list[ft.Control] = []
        for item in items:
            iid = int(item.get("item_id"))
            cards.append(
                ft.Container(
                    width=tile_width,
                    content=card(ft.Column(spacing=8, controls=[
                        ft.Container(
                            height=120,
                            border_radius=10,
                            bgcolor=soft_orange,
                            alignment=ft.Alignment(0, 0),
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            content=(
                                ft.Image(
                                    src=item.get("image_url", ""),
                                    width=tile_width,
                                    height=120,
                                    fit="cover",
                                    error_content=ft.Text("No Image", color=text_muted, size=11),
                                )
                                if item.get("image_url")
                                else ft.Text("No Image", color=text_muted, size=11)
                            ),
                        ),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Text(item.get("name", "Item"), size=20, weight=ft.FontWeight.BOLD, color=text_dark, font_family="Georgia", expand=True),
                            ft.Text(f"Rs {float(str(item.get('price', 0) or 0)):.2f}", size=16, weight=ft.FontWeight.BOLD, color=accent),
                        ]),
                        ft.Text(item.get("desc", ""), size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, color=text_muted),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            status_chip("available" if item.get("is_available") else "sold out"),
                            ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=text_muted, on_click=lambda e, menu_item=item: open_menu_edit_dialog(menu_item)),
                        ]),
                        ft.Row(controls=[
                            ft.OutlinedButton("Toggle", on_click=lambda e, id_=iid: page.run_task(handle_menu_toggle, id_)),
                            ft.OutlinedButton("Delete", on_click=lambda e, id_=iid: page.run_task(handle_menu_delete, id_)),
                        ]),
                    ])),
                )
            )

        card_rows: list[ft.Control] = []
        for i in range(0, len(cards), cols):
            card_rows.append(ft.Row(spacing=12, scroll=ft.ScrollMode.AUTO, controls=cards[i:i + cols]))

        return ft.Container(expand=True, bgcolor=page_bg, content=ft.Column(expand=True, spacing=0, controls=[
            header_bar(),
            ft.Container(expand=True, padding=14, content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=12, controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text("Menu Management", size=21 if (page.width or 390) < 500 else 24, weight=ft.FontWeight.BOLD, color=text_dark, font_family="Georgia"),
                                ft.Text("Manage dishes and availability.", size=12, color=text_muted),
                            ],
                        ),
                        ft.Row(
                            spacing=8,
                            controls=[
                                elevated_btn("Add Item", icon=ft.Icons.ADD, style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff", shape=ft.RoundedRectangleBorder(radius=12)), on_click=lambda e: open_menu_create_dialog()),
                                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=accent, on_click=lambda e: page.run_task(refresh_tab, 3)),
                            ],
                        ),
                    ],
                ),
                ft.TextField(prefix_icon=ft.Icons.SEARCH, hint_text="Search menu items...", value=ui["menu_search"], on_change=lambda e: _set_ui("menu_search", e.control.value), border_radius=14, bgcolor=input_bg, border_color=input_bg),
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    *[chip_button(c.title() if c != "all" else "All Items", selected == c.lower(), (lambda v: (lambda e: _set_ui("menu_filter", v)))(c.lower())) for c in categories_unique[:8]]
                ]),
                *(card_rows if card_rows else [ft.Text("No menu items found.", color=text_muted)]),
            ])),
        ]))

    def more_tabs_bar() -> ft.Control:
        active = str(ui.get("more_section") or "customers").lower()
        return ft.Row(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                chip_button("Customers", active == "customers", lambda e: _set_ui("more_section", "customers")),
                chip_button("Staff", active == "staff", lambda e: _set_ui("more_section", "staff")),
                chip_button("Reviews", active == "reviews", lambda e: _set_ui("more_section", "reviews")),
            ],
        )

    def build_customers(in_more: bool = False) -> ft.Control:
        selected = ui["customers_filter"]
        search = ui["customers_search"].strip().lower()
        customers = state["customers"]
        if search:
            customers = [c for c in customers if search in str(c.get("name", "")).lower() or search in str(c.get("email", "")).lower()]
        if selected != "all":
            customers = [c for c in customers if str(c.get("status", "")).lower() == selected]

        cards: list[ft.Control] = []
        for c in customers:
            name = c.get("name") or "Customer"
            cards.append(
                card(ft.Column(spacing=8, controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Row(spacing=10, controls=[
                            _avatar(name),
                            ft.Column(spacing=1, controls=[ft.Text(name, size=18, weight=ft.FontWeight.W_600, color=text_dark, font_family="Georgia"), ft.Text("Joined recently", color=text_muted)]),
                        ]),
                        status_chip(c.get("status", "regular")),
                    ]),
                    ft.Divider(height=6, color=line_color),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Column(spacing=1, controls=[ft.Text("TOTAL SPEND", size=11, color=text_muted), ft.Text(f"Rs {float(str(c.get('total_spent', 0) or 0)):.2f}", size=30 if (page.width or 390) > 600 else 27, color=text_dark, font_family="Georgia")]),
                        ft.TextButton("View Details >", style=ft.ButtonStyle(color=accent), on_click=lambda e, customer=c: open_customer_dialog(customer)),
                    ]),
                ]))
            )

        return ft.Container(expand=True, bgcolor=page_bg, content=ft.Column(expand=True, spacing=0, controls=[
            header_bar(),
            ft.Container(expand=True, padding=14, content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=12, controls=[
                *([more_tabs_bar()] if in_more else []),
                section_header("Customer Management", "Review and manage your diner relationships.", 4),
                ft.TextField(prefix_icon=ft.Icons.SEARCH, hint_text="Search by name or email...", value=ui["customers_search"], on_change=lambda e: _set_ui("customers_search", e.control.value), border_radius=14, bgcolor=input_bg, border_color=input_bg),
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    chip_button("All Customers", selected == "all", lambda e: _set_ui("customers_filter", "all")),
                    chip_button("VIP", selected == "vip", lambda e: _set_ui("customers_filter", "vip")),
                    chip_button("Regular", selected == "regular", lambda e: _set_ui("customers_filter", "regular")),
                ]),
                *(cards if cards else [ft.Text("No customers found.", color=text_muted)]),
            ])),
        ]))

    def build_staff(in_more: bool = False) -> ft.Control:
        selected = ui["staff_filter"]
        staff = state["staff"]
        search_query = str(ui.get("staff_search") or "").strip().lower()
        if search_query:
            staff = [
                s for s in staff
                if search_query in str(s.get("name") or "").lower()
                or search_query in str(s.get("email") or "").lower()
            ]
        if selected == "admins":
            staff = [s for s in staff if bool(s.get("is_admin"))]
        elif selected == "chefs":
            staff = [s for s in staff if "chef" in str(s.get("name", "")).lower() or "chef" in str(s.get("email", "")).lower()]

        invite_email = ft.TextField(
            label="Staff email",
            width=260,
            value=ui.get("staff_invite_email", ""),
            on_change=lambda e: _set_ui("staff_invite_email", e.control.value),
        )
        invite_role = ft.Dropdown(
            width=120,
            value=ui.get("staff_invite_role", "staff"),
            options=[ft.dropdown.Option("staff"), ft.dropdown.Option("admin")],
        )

        cards: list[ft.Control] = []
        for s in staff:
            sid = int(s.get("id"))
            name = s.get("name") or "Staff"
            status_value = "active" if s.get("is_admin") else "on_shift"
            cards.append(card(ft.Column(spacing=8, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Row(spacing=10, controls=[
                        _avatar(name),
                        ft.Column(spacing=1, controls=[ft.Text(name, size=17, weight=ft.FontWeight.W_600, color=text_dark), ft.Text("ADMINISTRATOR" if s.get("is_admin") else "STAFF", color=text_muted)]),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=16, icon_color=text_muted, on_click=lambda e, staff_item=s: open_staff_edit_dialog(staff_item)),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=16, icon_color="#c03b2f", on_click=lambda e, id_=sid: page.run_task(handle_staff_action, id_, "remove_access")),
                    ]),
                ]),
                ft.Row(controls=[status_chip(status_value)]),
                ft.Divider(height=6, color=line_color),
                ft.Text(s.get("email") or "", color=text_muted),
                ft.Row(controls=[
                    ft.OutlinedButton("Make Admin", on_click=lambda e, id_=sid: page.run_task(handle_staff_action, id_, "make_admin")),
                    ft.OutlinedButton("Make Staff", on_click=lambda e, id_=sid: page.run_task(handle_staff_action, id_, "make_staff")),
                    ft.OutlinedButton("Reset Password", on_click=lambda e, id_=sid: page.run_task(handle_staff_action, id_, "reset_password")),
                ], wrap=True),
            ])))

        return ft.Container(expand=True, bgcolor=page_bg, content=ft.Column(expand=True, spacing=0, controls=[
            header_bar(),
            ft.Container(expand=True, padding=14, content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=12, controls=[
                *([more_tabs_bar()] if in_more else []),
                section_header("Staff Management", "OPERATIONS", 5),
                card(ft.Column(spacing=10, controls=[
                    ft.Row(controls=[invite_email, invite_role], wrap=True),
                    elevated_btn("Invite Staff", icon=ft.Icons.PERSON_ADD_ALT_1_OUTLINED, style=ft.ButtonStyle(bgcolor=primary_btn, color="#ffffff", shape=ft.RoundedRectangleBorder(radius=12)), on_click=lambda e: page.run_task(handle_invite_staff, invite_email.value, invite_role.value)),
                ])),
                ft.TextField(prefix_icon=ft.Icons.SEARCH, hint_text="Search by name or email...", value=ui["staff_search"], on_change=lambda e: _set_ui("staff_search", e.control.value), border_radius=14, bgcolor=input_bg, border_color=input_bg),
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    chip_button("All Staff", selected == "all", lambda e: _set_ui("staff_filter", "all")),
                    chip_button("Admins", selected == "admins", lambda e: _set_ui("staff_filter", "admins")),
                    chip_button("Chefs", selected == "chefs", lambda e: _set_ui("staff_filter", "chefs")),
                ]),
                *(cards if cards else [ft.Text("No staff found.", color=text_muted)]),
            ])),
        ]))

    def build_reviews(in_more: bool = False) -> ft.Control:
        selected = ui["reviews_filter"]
        reviews = state["reviews"]
        if selected == "pending":
            reviews = [r for r in reviews if not bool(r.get("is_verified"))]
        elif selected == "approved":
            reviews = [r for r in reviews if bool(r.get("is_verified"))]

        stats = state["review_stats"]
        avg = float(stats.get("avg_rating") or 0)
        total_reviews = int(stats.get("total_reviews") or len(state["reviews"]))

        cards: list[ft.Control] = []
        for r in reviews:
            name = r.get("user_name") or "Guest"
            rid = int(r.get("review_id"))
            stars = int(r.get("rating") or 0)
            stars_text = ("*" * stars).ljust(5, "*")
            cards.append(card(ft.Column(spacing=8, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Row(spacing=10, controls=[
                        _avatar(name),
                        ft.Column(spacing=1, controls=[
                            ft.Text(name, size=16, weight=ft.FontWeight.W_600, color=text_dark),
                            ft.Text(stars_text, color=accent),
                        ]),
                    ]),
                    ft.Text("2h ago", color="#9ca3af", size=11),
                ]),
                ft.Text(f'"{r.get("review_text", "")}"', size=13, color=text_muted, italic=True),
                ft.Divider(height=6, color=line_color),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.TextButton("Email Response", icon=ft.Icons.MAIL_OUTLINE, style=ft.ButtonStyle(color=accent), on_click=lambda e, review=r: open_email_dialog(review)),
                    ft.Row(controls=[
                        ft.OutlinedButton("Approve", on_click=lambda e, id_=rid: page.run_task(handle_review_action, id_, "verify"), visible=not bool(r.get("is_verified"))),
                        ft.OutlinedButton("Delete", on_click=lambda e, id_=rid: page.run_task(handle_review_action, id_, "delete")),
                    ]),
                ]),
            ])))

        return ft.Container(expand=True, bgcolor=page_bg, content=ft.Column(expand=True, spacing=0, controls=[
            header_bar(),
            ft.Container(expand=True, padding=14, content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=12, controls=[
                *([more_tabs_bar()] if in_more else []),
                ft.Row(spacing=10, controls=[
                    metric_card("AVERAGE RATING", f"{avg:.1f}", "*****", ft.Icons.STAR_OUTLINE),
                    metric_card("TOTAL REVIEWS", f"{total_reviews:,}", "", ft.Icons.TRENDING_UP),
                ]),
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    chip_button("All", selected == "all", lambda e: _set_ui("reviews_filter", "all")),
                    chip_button("Pending", selected == "pending", lambda e: _set_ui("reviews_filter", "pending")),
                    chip_button("Approved", selected == "approved", lambda e: _set_ui("reviews_filter", "approved")),
                ]),
                *(cards if cards else [ft.Text("No reviews found.", color=text_muted)]),
            ])),
        ]))

    def _set_ui(key: str, value):
        ui[key] = value
        render(page.navigation_bar.selected_index)

    def go_to_orders():
        page.navigation_bar.selected_index = 1
        render(1)

    def render(index: int):
        if index == 0:
            content.content = build_overview()
        elif index == 1:
            content.content = build_orders()
        elif index == 2:
            content.content = build_reservations()
        elif index == 3:
            content.content = build_menu()
        elif index == 4 and ui.get("more_section") == "staff":
            content.content = build_staff(in_more=True)
        elif index == 4 and ui.get("more_section") == "reviews":
            content.content = build_reviews(in_more=True)
        elif index == 4:
            content.content = build_customers(in_more=True)
        else:
            content.content = build_overview()
        page.update()

    def on_nav_change(e: ft.ControlEvent):
        render(int(e.data))

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        indicator_color=soft_orange,
        bgcolor="#ffffff",
        label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.GRID_VIEW_OUTLINED, selected_icon=ft.Icons.GRID_VIEW, label="Dashboard"),
            ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG_OUTLINED, selected_icon=ft.Icons.RECEIPT_LONG, label="Orders"),
            ft.NavigationBarDestination(icon=ft.Icons.EVENT_SEAT_OUTLINED, selected_icon=ft.Icons.EVENT_SEAT, label="Reservations"),
            ft.NavigationBarDestination(icon=ft.Icons.RESTAURANT_MENU_OUTLINED, selected_icon=ft.Icons.RESTAURANT_MENU, label="Menu"),
            ft.NavigationBarDestination(icon=ft.Icons.MORE_HORIZ_OUTLINED, selected_icon=ft.Icons.MORE_HORIZ, label="More"),
        ],
    )

    page.add(content)
    await load_all()
    render(0)
    page.run_task(live_orders_poll)


if __name__ == "__main__":
    ft.run(main)


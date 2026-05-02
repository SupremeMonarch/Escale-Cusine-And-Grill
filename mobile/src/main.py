import flet as ft
import asyncio
import os
import json
from urllib.parse import urlparse
from urllib import request, error
from home import HomeFeature
from menu import MenuFeature
from notifications import fetch_notification_events

from reservation import ReservationFeature
from review import ReviewFeature
from Registration import RegistrationFeature
from Login import LoginFeature
from settings import SettingsFeature


def main(page: ft.Page):
    page.title = "Escale Mobile"
    page.bgcolor = "#f5efe1"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    top_bar_host = ft.Container(height=56)
    content_host = ft.Container(expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE)
    sidebar_scrim = ft.Container(expand=True, visible=False, bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.BLACK))
    sidebar_panel_host = ft.Container(visible=False)
    login_scrim = ft.Container(expand=True, visible=False, bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLACK))
    login_panel_host = ft.Container(expand=True, visible=False)
    menu_feature: MenuFeature | None = None
    menu_view_cache: ft.Control | None = None
    home_feature: HomeFeature | None = None
    home_view_cache: ft.Control | None = None
    settings_feature: SettingsFeature | None = None
    notifications_enabled = True
    last_notification_cursor: str | None = None
    notifications_task_started = False
    notification_seen_ids: set[str] = set()
    sidebar_about_expanded = False
    sidebar_contact_expanded = False
    sidebar_faq_expanded = False
    sidebar_open = False
    route_history: list[str] = []
    current_route = "/"

    def _infer_api_base_url() -> str:
        explicit = (os.getenv("ECAG_API_BASE_URL") or "").strip()
        if explicit:
            return explicit.rstrip("/")

        try:
            parsed = urlparse(str(page.url or ""))
            host = (parsed.hostname or "").strip()
            if host and host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
                return f"http://{host}:8000"
        except Exception:
            pass

        # return "http://192.168.100.12:8000"
        return "http://127.0.0.1:8000"  #debug purposes, switch back to previous asap

    api_base_url = _infer_api_base_url().rstrip("/")

    auth_token: str | None = None
    auth_user: dict | None = None
    login_username_field = ft.TextField(label="Username", autofocus=True)
    login_password_field = ft.TextField(label="Password", password=True, can_reveal_password=True)
    login_status_text = ft.Text("", color="#8a3b00", size=12)

    def _api_json(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
        url = f"{api_base_url}{path}"
        headers = {"Accept": "application/json"}
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")
        if token:
            headers["Authorization"] = f"Token {token}"

        req = request.Request(url=url, headers=headers, data=payload, method=method)
        try:
            with request.urlopen(req, timeout=12) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Cannot reach backend: {exc.reason}") from exc

    def _resolve_account_type(user: dict) -> str:
        account_type = str(user.get("account_type") or "").lower().strip()
        if account_type in {"admin", "staff", "customer"}:
            return account_type
        if bool(user.get("is_superuser")):
            return "admin"
        if bool(user.get("is_staff")):
            return "staff"
        return "customer"

    async def _open_mobile_dashboard(account_type: str) -> None:
        if auth_token:
            page.session.store.set("token", auth_token)

        # Force-dismiss any modal that might still be active before switching shell.
        try:
            for control in list(page.overlay):
                if isinstance(control, ft.AlertDialog):
                    control.open = False
            page.overlay.clear()
        except Exception:
            pass
        try:
            page.dialog = None
        except Exception:
            pass

        # Replace the current shell with the role-specific mobile dashboard app.
        page.clean()
        page.bottom_appbar = None
        page.navigation_bar = None
        page.floating_action_button = None
        page.update()
        try:
            if account_type == "admin":
                from admin_mobile import main as admin_mobile_main

                await admin_mobile_main(page)
                return

            if account_type == "staff":
                from staff_dash import main as staff_dashboard_main

                await staff_dashboard_main(page)
                return

            from customer_dash import main as customer_dashboard_main

            await customer_dashboard_main(page)
        except Exception as exc:
            # Show a visible error instead of leaving a blank screen if a role dashboard crashes.
            page.clean()
            page.add(
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    padding=20,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                        controls=[
                            ft.Text("Dashboard failed to open", size=22, weight=ft.FontWeight.BOLD, color="#2f2a24"),
                            ft.Text(f"{account_type.title()} dashboard error: {exc}", size=13, color="#8a3b00", text_align=ft.TextAlign.CENTER),
                            ft.ElevatedButton("Return to Main App", on_click=lambda e: main(page)),
                        ],
                    ),
                )
            )
            page.update()

    async def route_for_account(user: dict) -> None:
        account_type = _resolve_account_type(user)
        await _open_mobile_dashboard(account_type)

    async def open_dashboard(e=None) -> None:
        nonlocal auth_user
        if auth_token:
            try:
                refreshed = await asyncio.to_thread(_api_json, "GET", "/api/auth/me/", None, auth_token)
                if isinstance(refreshed, dict) and refreshed:
                    auth_user = refreshed
                    try:
                        page.client_storage.set("auth.user", json.dumps(auth_user))
                    except Exception:
                        pass
            except Exception:
                pass
        await route_for_account(auth_user or {})

    def logout_account(e=None) -> None:
        nonlocal auth_token, auth_user
        token = auth_token
        auth_token = None
        auth_user = None
        try:
            page.client_storage.remove("auth.token")
            page.client_storage.remove("auth.user")
        except Exception:
            pass
        if token:
            try:
                _api_json("POST", "/api/auth/logout/", token=token)
            except Exception:
                pass
        top_bar_host.content = build_top_bar()
        page.snack_bar = ft.SnackBar(content=ft.Text("Logged out."), open=True, bgcolor="#2f2a24")
        page.update()

    def close_login_overlay(e=None):
        login_scrim.visible = False
        login_panel_host.visible = False
        login_status_text.value = ""
        page.update()

    async def submit_login(e=None):
        nonlocal auth_token, auth_user


        username = (login_username_field.value or "").strip()
        password = login_password_field.value or ""

        
        
        if not username or not password:

            login_status_text.value = "Enter username and password."
            page.update()
            return

        try:

            token_payload = await asyncio.to_thread(
                _api_json,
                "POST",
                "/api/auth/login/",
                {"username": username, "password": password},
                None,
            )



            token = token_payload.get("token")





            if not token:
                raise RuntimeError("Login failed: token not returned.")




            me_payload = await asyncio.to_thread(_api_json, "GET", "/api/auth/me/", None, token)





            auth_token = token
            auth_user = me_payload





            try:
                page.client_storage.set("auth.token", auth_token)
                page.client_storage.set("auth.user", json.dumps(auth_user))
            except Exception:                                               
                pass                                                          




            close_login_overlay()
            login_password_field.value = ""

            await asyncio.sleep(0)

 
            top_bar_host.content = build_top_bar()


            await route_for_account(auth_user)

            page.snack_bar = ft.SnackBar(content=ft.Text("Login successful."), open=True, bgcolor="#2f2a24")
            page.update()

        except Exception as exc:
            print(f"[DEBUG ERROR] {exc}")
            login_status_text.value = str(exc)
            page.update()

    def refresh_login_panel() -> None:
        login_panel_host.content = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=360,
                bgcolor="#f8f8f8",
                border_radius=18,
                padding=ft.Padding.only(left=20, right=20, top=18, bottom=14),
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text("Login", size=34, weight=ft.FontWeight.W_700, color="#2f2a24"),
                        login_username_field,
                        login_password_field,
                        login_status_text,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            controls=[
                                ft.TextButton("Register",on_click=lambda e: (close_login_overlay(),navigate("/signup"))),
                                ft.TextButton("Cancel", on_click=close_login_overlay),
                                ft.TextButton("Login", on_click=lambda e: page.run_task(submit_login, e)),
                            ],
                        ),
                    ],
                ),
            ),
        )

    def open_account_dialog(e=None) -> None:
        nonlocal auth_token, auth_user
        if auth_token and auth_user:
            page.run_task(open_dashboard)
            return

        login_status_text.value = ""
        login_password_field.value = ""
        refresh_login_panel()
        login_scrim.visible = True
        login_panel_host.visible = True
        page.update()

    def try_restore_session() -> None:
        nonlocal auth_token, auth_user
        restored_token: str | None = None
        restored_user: dict | None = None

        try:
            token = page.client_storage.get("auth.token")
            if token:
                restored_token = str(token)
        except Exception:
            pass

        if not restored_token:
            try:
                session_token = page.session.store.get("token")
                if session_token:
                    restored_token = str(session_token)
            except Exception:
                pass

        try:
            raw_user = page.client_storage.get("auth.user")
            if raw_user:
                if isinstance(raw_user, str):
                    restored_user = json.loads(raw_user)
                elif isinstance(raw_user, dict):
                    restored_user = raw_user
        except Exception:
            pass

        if restored_token and not restored_user:
            try:
                me_payload = _api_json("GET", "/api/auth/me/", None, restored_token)
                if isinstance(me_payload, dict) and me_payload:
                    restored_user = me_payload
                    try:
                        page.client_storage.set("auth.token", restored_token)
                        page.client_storage.set("auth.user", json.dumps(restored_user))
                    except Exception:
                        pass
            except Exception:
                pass

        auth_token = restored_token
        auth_user = restored_user

    def read_bool_setting(key: str, default: bool) -> bool:
        try:
            raw = page.client_storage.get(key)
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                return raw.lower() in {"1", "true", "yes", "on"}
        except Exception:
            pass
        return default

    def set_bool_setting(key: str, value: bool) -> None:
        try:
            page.client_storage.set(key, bool(value))
        except Exception:
            pass

    def set_notifications_enabled(value: bool) -> None:
        nonlocal notifications_enabled
        notifications_enabled = bool(value)
        set_bool_setting("settings.notifications_enabled", notifications_enabled)

    def set_location_enabled(value: bool) -> None:
        set_bool_setting("settings.location_enabled", bool(value))

    async def notification_poller():
        nonlocal last_notification_cursor
        while True:
            await asyncio.sleep(10)
            if not notifications_enabled:
                continue

            try:
                payload = fetch_notification_events(api_base_url, last_notification_cursor)
            except Exception:
                continue

            events = payload.get("events", [])
            server_time = payload.get("server_time")

            if last_notification_cursor is None:
                last_notification_cursor = server_time
                continue

            fresh_events = []
            for event in events:
                eid = event.get("event_id", "")
                timestamp = event.get("timestamp", "")
                unique_key = f"{eid}:{timestamp}"
                if unique_key in notification_seen_ids:
                    continue
                notification_seen_ids.add(unique_key)
                fresh_events.append(event)

            if fresh_events:
                latest = fresh_events[-1]
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(latest.get("message", "New update available")),
                    open=True,
                    bgcolor="#2f2a24",
                )
                page.update()

            last_notification_cursor = server_time or (events[-1].get("timestamp") if events else last_notification_cursor)

    def close_sidebar(e=None) -> None:
        nonlocal sidebar_open
        sidebar_open = False
        sidebar_scrim.visible = False
        sidebar_panel_host.visible = False
        page.update()

    def open_sidebar(e=None) -> None:
        nonlocal sidebar_open
        sidebar_open = True
        sidebar_scrim.visible = True
        sidebar_panel_host.visible = True
        refresh_sidebar_panel()
        page.update()

    sidebar_scrim.on_click = close_sidebar
    login_scrim.on_click = close_login_overlay

    def toggle_about(e=None) -> None:
        nonlocal sidebar_about_expanded
        sidebar_about_expanded = not sidebar_about_expanded
        refresh_sidebar_panel()
        page.update()

    def toggle_contact(e=None) -> None:
        nonlocal sidebar_contact_expanded
        sidebar_contact_expanded = not sidebar_contact_expanded
        refresh_sidebar_panel()
        page.update()

    def toggle_faq(e=None) -> None:
        nonlocal sidebar_faq_expanded
        sidebar_faq_expanded = not sidebar_faq_expanded
        refresh_sidebar_panel()
        page.update()

    def sidebar_expandable_row(title: str, expanded: bool, on_click) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=10),
            on_click=on_click,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(title, size=17, color="#3a342c"),
                    ft.Icon(
                        ft.Icons.KEYBOARD_ARROW_DOWN if not expanded else ft.Icons.KEYBOARD_ARROW_UP,
                        color="#FF5C00",
                        size=20,
                    ),
                ],
            ),
        )

    def sidebar_child_text(value: str) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.only(left=10, right=8, top=2, bottom=8),
            content=ft.Text(value, size=13, color="#6f665b"),
        )

    def sidebar_nav_row(title: str, route: str) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=10),
            on_click=lambda e: (close_sidebar(), navigate(route)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(title, size=17, color="#3a342c"),
                    ft.Icon(ft.Icons.ARROW_FORWARD, color="#FF5C00", size=16),
                ],
            ),
        )

    def refresh_sidebar_panel() -> None:
        about_details = [
            sidebar_child_text("Escale Cuisine & Grill serves authentic Mauritian flavors in a warm coastal setting."),
        ]
        contact_details = [
            sidebar_child_text("Phone: +230 5830 7677"),
            sidebar_child_text("Email: info@escale.com"),
            sidebar_child_text("Address: Coastal Rd, Flic en Flac, Mauritius"),
        ]
        faq_details = [
            sidebar_child_text("Do I need a reservation? Walk-ins are welcome, but reservations are recommended."),
            sidebar_child_text("Do you offer delivery? Yes, via our mobile ordering flow."),
            sidebar_child_text("Any vegetarian options? Yes, we have dedicated vegetarian dishes."),
        ]

        controls: list[ft.Control] = [
            ft.Container(
                padding=ft.Padding.only(bottom=14),
                content=ft.IconButton(icon=ft.Icons.CLOSE, icon_color="#FF5C00", on_click=close_sidebar),
            ),
            sidebar_expandable_row("About Us", sidebar_about_expanded, toggle_about),
        ]

        if sidebar_about_expanded:
            controls.extend(about_details)

        controls.append(sidebar_expandable_row("Contact Us", sidebar_contact_expanded, toggle_contact))
        if sidebar_contact_expanded:
            controls.extend(contact_details)

        controls.append(sidebar_expandable_row("Frequently Asked Questions", sidebar_faq_expanded, toggle_faq))
        if sidebar_faq_expanded:
            controls.extend(faq_details)

        controls.append(sidebar_nav_row("Reviews", "/review"))
        controls.append(sidebar_nav_row("Settings", "/settings"))

        sidebar_panel_host.content = ft.Container(
            width=min(int(page.width * 0.82), 330) if page.width else 300,
            expand=True,
            bgcolor="#ececec",
            padding=ft.Padding.only(left=12, right=12, top=8, bottom=20),
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, controls=controls),
        )

    def build_top_bar() -> ft.Control:
        person_icon_color = "#8a7765" if (auth_user or auth_token) else "#a39a92"
        account_control: ft.Control
        if auth_user or auth_token:
            account_control = ft.PopupMenuButton(
                icon=ft.Icons.PERSON,
                icon_color=person_icon_color,
                tooltip="Account",
                items=[
                    ft.PopupMenuItem("Dashboard", on_click=lambda e: page.run_task(open_dashboard, e)),
                    
                    ft.PopupMenuItem("Logout", on_click=logout_account),
                ],
            )
        # else:
        #     account_control = ft.IconButton(
        #         icon=ft.Icons.PERSON,
        #         icon_color=person_icon_color,
        #         tooltip="Account",
        #         on_click=open_account_dialog,
        #     )
        else:
            account_control = ft.PopupMenuButton(
                                                    icon=ft.Icons.PERSON,
                                                    icon_color=person_icon_color,
                                                    tooltip="Account",
                                                    items=  [
                                                                ft.PopupMenuItem("Login", on_click=open_account_dialog),
                                                                ft.PopupMenuItem("Register",on_click=lambda e: (close_login_overlay(),navigate("/signup"))),
                                                            ],
                                                            
                                                )
        
        return ft.Container(
            height=56,
            bgcolor="#f8f8f8",
            border=ft.Border.only(bottom=ft.BorderSide(1, "#e3e3e3")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(icon=ft.Icons.MENU, icon_color="#FF5C00", on_click=open_sidebar),
                    ft.Text(
                        "ESCALE CUISINE",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="#FF5C00",
                    ),
                    account_control,
                ],
            ),
        )

    def nav_item(label: str, icon: str, active: bool, route: str) -> ft.Control:
        color = "#FF5C00" if active else "#a9a3a0"
        return ft.Container(
            width=68,
            border_radius=10,
            padding=ft.Padding.symmetric(vertical=4),
            on_click=lambda e: navigate(route),
            content=ft.Column(
                spacing=1,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=24, color=color),
                    ft.Text(label, size=11, weight=ft.FontWeight.W_500, color=color),
                ],
            ),
        )

    def build_bottom_nav(active_route: str) -> ft.BottomAppBar:
        return ft.BottomAppBar(
            bgcolor="#f8f8f8",
            elevation=8,
            height=72,
            padding=0,
            content=ft.Container(
                border=ft.Border.only(top=ft.BorderSide(1, "#e3e3e3")),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        nav_item("HOME", ft.Icons.HOME, active_route == "/", "/"),
                        nav_item("MENU", ft.Icons.RESTAURANT_MENU, active_route.startswith("/menu"), "/menu"),
                        nav_item("BOOK", ft.Icons.CALENDAR_MONTH, active_route.startswith("/reservation"), "/reservation"),
                        nav_item("CART", ft.Icons.SHOPPING_BAG_OUTLINED, active_route.startswith("/cart"), "/cart"),
                    ],
                ),
            ),
        )

    def home_view() -> ft.Control:
        nonlocal home_feature, home_view_cache
        page.floating_action_button = None
        if home_feature is None:
            home_feature = HomeFeature(page, on_navigate=navigate, base_url=api_base_url)
        if home_view_cache is None:
            home_view_cache = home_feature.build_view()
        return home_view_cache

    def navigate(route: str, add_history: bool = True) -> None:
        nonlocal current_route, menu_view_cache, settings_feature, menu_feature
        if add_history and route != current_route:
            route_history.append(current_route)

        if route == "/review":
            page.floating_action_button = None
            content_host.content = review_feature.build_list_view()
        
        elif route == "/review/write":
            page.floating_action_button = None
            content_host.content = review_feature.build_write_view()
        
        elif route == "/reservation":
            page.floating_action_button = None
            content_host.content = reservation_feature.build_start_view()
        
        elif route == "/reservation/tables":
            page.floating_action_button = None
            content_host.content = reservation_feature.build_table_view()
        
        elif route == "/reservation/details":
            page.floating_action_button = None
            content_host.content = reservation_feature.build_details_view()
        
        elif route == "/reservation/confirmed":
            page.floating_action_button = None
            content_host.content = reservation_feature.build_confirmation_view()
        
        elif route == "/signup":
            page.floating_action_button = None
            content_host.content = registration_feature.build_signup_view()

        elif route == "/login":
            page.floating_action_button = None
            content_host.content = login_feature.build_login_view()

        elif route == "/menu":
            page.floating_action_button = None
            if menu_feature is None:
                menu_feature = MenuFeature(
                    page,
                    on_back=go_back,
                    base_url=api_base_url,
                    data_url=f"{api_base_url}/menu/mobile/data/",
                )
            if menu_view_cache is None:
                menu_view_cache = menu_feature.build_view()
            content_host.content = ft.Container(expand=True, content=menu_view_cache)
        elif route == "/cart":
            page.floating_action_button = None
            if menu_feature is None:
                menu_feature = MenuFeature(page, on_back=go_back)
            content_host.content = ft.Container(expand=True, content=menu_feature.build_view(active_view="cart"))
        elif route == "/settings":
            page.floating_action_button = None
            if settings_feature is None:
                settings_feature = SettingsFeature(
                    page,
                    notifications_enabled=notifications_enabled,
                    on_notifications_change=set_notifications_enabled,
                    location_enabled=read_bool_setting("settings.location_enabled", False),
                    on_location_change=set_location_enabled,
                )
            content_host.content = ft.Container(expand=True, content=settings_feature.build_view())
        else:
            content_host.content = ft.Container(expand=True, content=home_view())

        current_route = route
        top_bar_host.content = build_top_bar()
        page.bottom_appbar = build_bottom_nav(current_route)
        close_sidebar()
        page.route = route
        page.update()

    def go_back() -> None:
        previous_route = route_history.pop() if route_history else "/"
        navigate(previous_route, add_history=False)

    review_feature = ReviewFeature(page, on_navigate=navigate)
    reservation_feature = ReservationFeature(page, on_navigate=navigate, on_back=go_back)
    registration_feature = RegistrationFeature(page, on_navigate=navigate)
    registration_feature.setup()
    login_feature = LoginFeature(page, on_navigate=navigate)
    notifications_enabled = read_bool_setting("settings.notifications_enabled", True)
    try_restore_session()

    if not notifications_task_started:
        notifications_task_started = True
        page.run_task(notification_poller)

    page.bottom_appbar = build_bottom_nav(current_route)

    page.add(
        ft.Container(
            expand=True,
            bgcolor="#f5efe1",
            content=ft.Stack(
                expand=True,
                controls=[
                    ft.Container(expand=True, padding=ft.Padding.only(top=56), content=content_host),
                    ft.Container(top=0, left=0, right=0, content=top_bar_host),
                    sidebar_scrim,
                    ft.Container(
                        left=0,
                        top=0,
                        bottom=0,
                        content=sidebar_panel_host,
                    ),
                    login_scrim,
                    login_panel_host,
                ],
            ),
        )
    )
    navigate("/")

if __name__ == "__main__":
    ft.run(main)

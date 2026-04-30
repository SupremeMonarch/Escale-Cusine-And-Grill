import flet as ft
import asyncio
import os
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

    api_base_url = os.getenv("ECAG_API_BASE_URL", "http://127.0.0.1:8000")

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
            padding=ft.padding.symmetric(vertical=10),
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
            padding=ft.padding.only(left=10, right=8, top=2, bottom=8),
            content=ft.Text(value, size=13, color="#6f665b"),
        )

    def sidebar_nav_row(title: str, route: str) -> ft.Control:
        return ft.Container(
            padding=ft.padding.symmetric(vertical=10),
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
                padding=ft.padding.only(bottom=14),
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
            padding=ft.padding.only(left=12, right=12, top=8, bottom=20),
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, controls=controls),
        )

    def build_top_bar() -> ft.Control:
        return ft.Container(
            height=56,
            bgcolor="#f8f8f8",
            border=ft.border.only(bottom=ft.BorderSide(1, "#e3e3e3")),
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
                    ft.Container(
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor="#e8dcc8",
                        alignment=ft.Alignment.CENTER,
                        margin=ft.margin.only(right=10),
                        content=ft.Icon(ft.Icons.PERSON, size=18, color="#8a7765"),
                    ),
                ],
            ),
        )

    def nav_item(label: str, icon: str, active: bool, route: str) -> ft.Control:
        color = "#FF5C00" if active else "#a9a3a0"
        return ft.Container(
            width=68,
            border_radius=10,
            padding=ft.padding.symmetric(vertical=4),
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
                border=ft.border.only(top=ft.BorderSide(1, "#e3e3e3")),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        nav_item("HOME", ft.Icons.HOME, active_route == "/", "/"),
                        nav_item("MENU", ft.Icons.RESTAURANT_MENU, active_route.startswith("/menu"), "/menu"),
                        nav_item("BOOK", ft.Icons.CALENDAR_MONTH, active_route.startswith("/reservation"), "/reservation"),
                        nav_item("CART", ft.Icons.SHOPPING_BAG_OUTLINED, False, "/menu"),
                    ],
                ),
            ),
        )

    def home_view() -> ft.Control:
        nonlocal home_feature, home_view_cache
        page.floating_action_button = None
        if home_feature is None:
            home_feature = HomeFeature(page, on_navigate=navigate)
        if home_view_cache is None:
            home_view_cache = home_feature.build_view()
        return home_view_cache

    def navigate(route: str, add_history: bool = True) -> None:
        nonlocal current_route, menu_view_cache, settings_feature
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
            nonlocal menu_feature
            page.floating_action_button = None
            if menu_feature is None:
                menu_feature = MenuFeature(page, on_back=go_back)
            if menu_view_cache is None:
                menu_view_cache = menu_feature.build_view()
            content_host.content = ft.Container(expand=True, content=menu_view_cache)
        elif route == "/settings":
            page.floating_action_button = None
            if settings_feature is None:
                settings_feature = SettingsFeature(
                    page,
                    notifications_enabled=notifications_enabled,
                    on_notifications_change=set_notifications_enabled,
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
                    ft.Container(expand=True, padding=ft.padding.only(top=56), content=content_host),
                    ft.Container(top=0, left=0, right=0, content=top_bar_host),
                    sidebar_scrim,
                    ft.Container(
                        left=0,
                        top=0,
                        bottom=0,
                        content=sidebar_panel_host,
                    ),
                ],
            ),
        )
    )
    navigate("/")


ft.run(main)

import flet as ft
from home import HomeFeature
from menu import MenuFeature

from reservation import ReservationFeature
from review import ReviewFeature


def main(page: ft.Page):
    page.title = "Escale Mobile"
    page.bgcolor = "#f5efe1"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    content_host = ft.Container(expand=True)
    top_bar_host = ft.Container()
    bottom_nav_host = ft.Container()
    menu_feature: MenuFeature | None = None
    menu_view_cache: ft.Control | None = None
    home_feature: HomeFeature | None = None
    home_view_cache: ft.Control | None = None
    route_history: list[str] = []
    current_route = "/"

    def build_top_bar() -> ft.Control:
        return ft.Container(
            height=56,
            bgcolor="#f8f8f8",
            padding=ft.padding.symmetric(horizontal=8),
            border=ft.border.only(bottom=ft.BorderSide(1, "#e3e3e3")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(icon=ft.Icons.MENU, icon_color="#e57722"),
                    ft.Text(
                        "ESCALE CUISINE",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="#e57722",
                    ),
                    ft.Container(
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor="#e8dcc8",
                        alignment=ft.Alignment.CENTER,
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

    def build_bottom_nav(active_route: str) -> ft.Control:
        return ft.Container(
            height=72,
            bgcolor="#f8f8f8",
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
        nonlocal current_route, menu_view_cache
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
        elif route == "/menu":
            nonlocal menu_feature
            page.floating_action_button = None
            if menu_feature is None:
                menu_feature = MenuFeature(page, on_back=go_back)
            if menu_view_cache is None:
                menu_view_cache = menu_feature.build_view()
            content_host.content = menu_view_cache
        else:
            content_host.content = home_view()

        current_route = route
        top_bar_host.content = build_top_bar()
        bottom_nav_host.content = build_bottom_nav(current_route)
        page.route = route
        page.update()

    def go_back() -> None:
        previous_route = route_history.pop() if route_history else "/"
        navigate(previous_route, add_history=False)

    review_feature = ReviewFeature(page, on_navigate=navigate)
    reservation_feature = ReservationFeature(page, on_navigate=navigate, on_back=go_back)
    page.add(
        ft.Container(
            expand=True,
            bgcolor="#f5efe1",
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    top_bar_host,
                    ft.Container(expand=True, content=content_host),
                    bottom_nav_host,
                ],
            ),
        )
    )
    navigate("/")


ft.run(main)

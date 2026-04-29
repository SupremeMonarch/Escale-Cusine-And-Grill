import os
from dotenv import load_dotenv
import flet as ft
from utils.dashboard_utils import COLORS, FONT_FAMILY, FONT_URL, build_theme
from staff.staff_overview import get_staff_overview_view
from staff.staff_orders import get_staff_orders_view
from staff.staff_res import get_staff_res_view

load_dotenv()

async def main(page: ft.Page):
    DEV_TOKEN = os.environ.get("STAFF_TOKEN", "")
    page.session.store.set("token", DEV_TOKEN)

    page.title      = "Escale Cuisine and Grill"
    page.bgcolor    = COLORS["background"]
    page.padding    = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts      = {FONT_FAMILY: FONT_URL}
    page.theme      = build_theme()

    header = ft.Container(
        content=ft.Row(
            [
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color=COLORS["primary"]),
                    ft.Text("Escale", size=24, weight=ft.FontWeight.BOLD, color=COLORS["on_surface"]),
                ]),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON), radius=20),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        padding=ft.Padding.only(left=24, right=24, top=10, bottom=8),
        bgcolor=COLORS["background"]
    )

    content_area = ft.Container(expand=True)

    def navigate_to(index):
        page.navigation_bar.selected_index = index
        if index == 0:
            content_area.content = get_staff_overview_view(page, navigate_to)
        elif index == 1:
            content_area.content = get_staff_orders_view(page)
        elif index == 2:
            content_area.content = get_staff_res_view(page)
        page.update()

    def on_nav_change(e):
        navigate_to(int(e.data))

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label="Home"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.RESTAURANT_OUTLINED,
                selected_icon=ft.Icons.RESTAURANT,
                label="Orders"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.EVENT_AVAILABLE_OUTLINED,
                selected_icon=ft.Icons.EVENT_AVAILABLE,
                label="Bookings"
            )
        ],
        bgcolor=COLORS["surface"],
        indicator_color=COLORS["indicator"],
        selected_index=0,
        height=70,
        elevation=10,
        label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
        on_change=on_nav_change
    )

    content_area.content = get_staff_overview_view(page, navigate_to)

    page.add(
        ft.Column(
            [header, content_area],
            spacing=0,
            expand=True
        )
    )

ft.run(main)

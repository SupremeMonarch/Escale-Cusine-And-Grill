from dotenv import load_dotenv
import os
import flet as ft
from utils.dashboard_utils import COLORS, FONT_FAMILY, FONT_URL, build_theme
from customer.customer_overview import get_overview_view
from customer.customer_orders import get_orders_view
from customer.customer_res import get_res_view
from customer.customer_profile import get_profile_view

load_dotenv()

async def main(page: ft.Page):
    try:
        page.dialog = None
        page.overlay.clear()
    except Exception:
        pass

    existing_token = page.session.store.get("token")
    if existing_token:
        page.session.store.set("token", existing_token)
    else:
        dev_token = os.environ.get("CUSTOMER_TOKEN", "")
        page.session.store.set("token", dev_token)

    page.title      = "Escale Cuisine and Grill"
    page.bgcolor    = COLORS["background"]
    page.padding    = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts      = {FONT_FAMILY: FONT_URL}
    page.theme      = build_theme()

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

    header = ft.Container(
        height=56,
        bgcolor="#f8f8f8",
        border=ft.Border.only(bottom=ft.BorderSide(1, "#e3e3e3")),
        content=ft.Row(
            [
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color="#FF5C00", on_click=lambda e: page.run_task(go_back_to_main_app, e)),
                    ft.Text("ESCALE CUISINE", size=16, weight=ft.FontWeight.BOLD, color="#FF5C00"),
                ]),
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
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.only(left=12, right=12, top=0, bottom=0),
    )

    content_area = ft.Container(expand=True)

    def navigate_to(index):
        page.navigation_bar.selected_index = index
        if index == 0:
            content_area.content = get_overview_view(page, navigate_to)
        elif index == 1:
            content_area.content = get_orders_view(page)
        elif index == 2:
            content_area.content = get_res_view(page)
        elif index == 3:
            content_area.content = get_profile_view(page)
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
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PERSON_OUTLINE,
                selected_icon=ft.Icons.PERSON,
                label="Profile"
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

    content_area.content = get_overview_view(page, navigate_to)

    page.add(
        ft.Column(
            [header, content_area],
            spacing=0,
            expand=True
        )
    )

if __name__ == "__main__":
    ft.run(main)

import os
import flet as ft
from utils.dashboard_utils import COLORS, FONT_FAMILY, FONT_URL, build_theme
from staff.staff_overview import get_staff_overview_view
from staff.staff_orders import get_staff_orders_view
from staff.staff_res import get_staff_res_view

async def main(page: ft.Page):
    import traceback
    try:
        page.dialog = None
        page.overlay.clear()
    except Exception:
        pass

    existing_token = page.session.store.get("token")
    if existing_token:
        page.session.store.set("token", existing_token)
    else:
        dev_token = os.environ.get("STAFF_TOKEN", "")
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
        border=ft.border.only(bottom=ft.BorderSide(1, "#e3e3e3")),
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
        padding=ft.padding.only(left=12, right=12, top=0, bottom=0),
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

    try:
        content_area.content = get_staff_overview_view(page, navigate_to)
    except Exception as exc:
        content_area.content = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            padding=20,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
                controls=[
                    ft.Text("Staff overview load error", size=18, weight=ft.FontWeight.BOLD, color="#8a3b00"),
                    ft.Text(traceback.format_exc(), size=10, color="#2f2a24", selectable=True),
                ],
            ),
        )

    page.add(
        ft.Column(
            [header, content_area],
            spacing=0,
            expand=True
        )
    )

if __name__ == "__main__":
    ft.run(main)

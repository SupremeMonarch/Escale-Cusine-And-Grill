import flet as ft

from reservation import ReservationFeature
from review import ReviewFeature


def main(page: ft.Page):
    page.title = "Escale Mobile"
    page.bgcolor = "#f5efe1"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    counter = ft.Text("0", size=50, data=0)
    content_host = ft.Container(expand=True)
    route_history: list[str] = []
    current_route = "/"

    def increment_click(e):
        counter.data += 1
        counter.value = str(counter.data)

    def home_view() -> ft.Control:
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=increment_click,
            bgcolor="#b24700",
            foreground_color="white",
        )
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=30,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=18,
                    controls=[
                        ft.Text("Counter", size=24, weight=ft.FontWeight.BOLD, color="#6b655a"),
                        counter,
                        ft.ElevatedButton(
                            "Open Reviews",
                            on_click=lambda e: navigate("/review"),
                            style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                        ),
                        ft.ElevatedButton(
                            "Open Reservations",
                            on_click=lambda e: navigate("/reservation"),
                            style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                        ),
                    ],
                ),
            ),
        )

    def navigate(route: str, add_history: bool = True) -> None:
        nonlocal current_route
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
        else:
            content_host.content = home_view()

        current_route = route
        page.route = route
        page.update()

    def go_back() -> None:
        previous_route = route_history.pop() if route_history else "/"
        navigate(previous_route, add_history=False)

    review_feature = ReviewFeature(page, on_navigate=navigate)
    reservation_feature = ReservationFeature(page, on_navigate=navigate, on_back=go_back)
    page.add(content_host)
    navigate("/")


ft.run(main)

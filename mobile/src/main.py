import flet as ft
from menu import MenuFeature

from reservation import ReservationFeature
from review import ReviewFeature
from Registration import RegistrationFeature
from Login import LoginFeature


def main(page: ft.Page):
    page.title = "Escale Mobile"
    page.bgcolor = "#f5efe1"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    counter = ft.Text("0", size=50, data=0)
    content_host = ft.Container(expand=True)
    menu_feature: MenuFeature | None = None
    menu_view_cache: ft.Control | None = None
    route_history: list[str] = []
    current_route = "/"

    def increment_click(e):
        counter.data += 1
        counter.value = str(counter.data)

    def home_view() -> ft.Control:
        page.floating_action_button = ft.FloatingActionButton   (
                                                                    icon=ft.Icons.ADD,
                                                                    on_click=increment_click,
                                                                    bgcolor="#b24700",
                                                                    foreground_color="white",
                                                                )
        return ft.SafeArea  (
                                expand=True,
                                content=ft.Container    (
                                                            expand=True,
                                                            padding=30,
                                                            content=ft.Column(
                                                                alignment=ft.MainAxisAlignment.CENTER,
                                                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                                spacing=18,
                                                                controls=   [
                                                                                ft.Text (
                                                                                            "Counter",
                                                                                            size=24, 
                                                                                            weight=ft.FontWeight.BOLD, 
                                                                                            color="#6b655a"
                                                                                        ),
                                                                                counter,
                                                                                ft.ElevatedButton   (
                                                                                                        "Open Reviews",
                                                                                                        on_click=lambda e: navigate("/review"),
                                                                                                        style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                                                                                                    ),
                                                                                ft.ElevatedButton   (
                                                                                                        "Open Reservations",
                                                                                                        on_click=lambda e: navigate("/reservation"),
                                                                                                        style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                                                                                                    ),
                                                                                                    
                                                                                ft.ElevatedButton   (
                                                                                                        "Open Menu",
                                                                                                        on_click=lambda e: navigate("/menu"),
                                                                                                        style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                                                                                                    ),
                                                                                
                                                                                ft.ElevatedButton   (
                                                                                                        "Login",
                                                                                                        on_click=lambda e: navigate("/login"),
                                                                                                        style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                                                                                                    ),

                                                                                ft.ElevatedButton   (
                                                                                                        "Sign-Up",
                                                                                                        on_click=lambda e: navigate("/signup"),
                                                                                                        style=ft.ButtonStyle(bgcolor="#b24700", color="white"),
                                                                                                    ),
                                                                            ],
                                                            ),
                                                        ),
                            )

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
            content_host.content = menu_view_cache
        
        

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


    registration_feature = RegistrationFeature(page, on_navigate=navigate)
    registration_feature.setup()

    login_feature=LoginFeature(page, on_navigate=navigate)


    page.add(content_host)
    navigate("/")


ft.run(main)

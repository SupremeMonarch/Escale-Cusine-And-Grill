from __future__ import annotations

from collections.abc import Callable

import flet as ft

from home.service import fetch_featured_dishes
from menu.service import resolve_image_payload


class HomeFeature:
    def __init__(
        self,
        page: ft.Page,
        on_navigate: Callable[[str], None] | None = None,
    ):
        self.page = page
        self.on_navigate = on_navigate
        self.featured_dishes = self._load_featured_dishes()

    # ------------------------------------------------------------------ #
    #  Public build method
    # ------------------------------------------------------------------ #

    def build_view(self) -> ft.Control:
        content_width = self._content_width(460)

        return ft.Container(
            expand=True,
            bgcolor="#f5efe1",
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Container(
                width=content_width,
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=0,
                    controls=[
                        self._build_logo_badge(),
                        self._build_tagline(),
                        self._build_description_section(),
                        self._build_featured_dishes(),
                        self._build_experience_section(),
                        ft.Container(height=18),
                    ],
                ),
            ),
        )

    # ------------------------------------------------------------------ #
    #  Sections
    # ------------------------------------------------------------------ #

    def _build_logo_badge(self) -> ft.Control:
        fit_contain = ft.BoxFit.CONTAIN if hasattr(ft, "BoxFit") else "contain"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=24),
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                width=210,
                height=210,
                border_radius=20,
                bgcolor="#e8b88f",
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=18,
                    color=ft.Colors.with_opacity(0.28, "#FF5C00"),
                    offset=ft.Offset(0, 8),
                ),
                alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src="Logo.png",
                    fit=fit_contain,
                    width=210,
                    height=210,
                ),
            ),
        )

    def _build_tagline(self) -> ft.Control:
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20),
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                "AUTHENTIC MAURITIAN GRILL",
                size=12,
                weight=ft.FontWeight.BOLD,
                color="#c25a1b",
                text_align=ft.TextAlign.CENTER,
            ),
        )

    def _build_description_section(self) -> ft.Control:
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
            content=ft.Column(
                spacing=18,
                controls=[
                    ft.Text(
                        "Escale Cuisine brings the warmth of the coastal grill to your table, featuring sustainably sourced ingredients and time-honored techniques.",
                        size=14,
                        color="#5a5249",
                        text_align=ft.TextAlign.LEFT,
                    ),
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(
                                expand=True,
                                bgcolor="#FF5C00",
                                border_radius=8,
                                padding=ft.padding.symmetric(vertical=12),
                                alignment=ft.Alignment.CENTER,
                                on_click=lambda e: self._navigate("/reservation"),
                                content=ft.Text(
                                    "Book a Table",
                                    color="white",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                bgcolor="#FFFFFF",
                                border_radius=8,
                                border=ft.Border.all(1, "#c9bfb0"),
                                padding=ft.padding.symmetric(vertical=12),
                                alignment=ft.Alignment.CENTER,
                                on_click=lambda e: self._navigate("/menu"),
                                content=ft.Text(
                                    "View Menu",
                                    color="#5a5249",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _build_featured_dishes(self) -> ft.Control:
        dish_cards = [self._dish_card(dish) for dish in self.featured_dishes]

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text(
                        "Featured Dishes",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color="#1a1a1a",
                    ),
                    ft.Row(spacing=12, scroll=ft.ScrollMode.AUTO, controls=dish_cards)
                    if dish_cards
                    else ft.Text("No featured dishes available right now.", size=13, color="#7a7a7a"),
                ],
            ),
        )

    def _dish_card(self, dish: dict) -> ft.Control:
        fit_cover = ft.BoxFit.COVER if hasattr(ft, "BoxFit") else "cover"
        image_payload = resolve_image_payload(dish.get("image_url", ""))
        image_control = (
            ft.Image(width=220, height=130, fit=fit_cover, **image_payload)
            if image_payload
            else ft.Icon(ft.Icons.RESTAURANT, size=48, color="#d4a574")
        )

        return ft.Container(
            width=220,
            border_radius=12,
            bgcolor="white",
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            on_click=lambda e: self._navigate("/menu"),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Container(
                        width=220,
                        height=130,
                        border_radius=ft.border_radius.only(top_left=12, top_right=12),
                        bgcolor="#f0f0f0",
                        alignment=ft.Alignment.CENTER,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=image_control,
                    ),
                    ft.Container(
                        padding=ft.padding.all(12),
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Text(
                                            dish.get("name", "Dish"),
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color="#1a1a1a",
                                            expand=True,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            f"Rs {dish.get('price', '0.00')}",
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color="#e57722",
                                        ),
                                    ],
                                ),
                                ft.Text(
                                    dish.get("desc", ""),
                                    size=11,
                                    color="#7a7a7a",
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Container(height=8),
                                ft.Container(
                                    bgcolor="#e57722",
                                    border_radius=6,
                                    padding=ft.padding.symmetric(vertical=8),
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Text(
                                        "Add to Cart",
                                        color="white",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _build_experience_section(self) -> ft.Control:
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Text(
                        "Choose Your Experience",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color="#1a1a1a",
                    ),
                    self._experience_card(
                        icon=ft.Icons.RESTAURANT,
                        title="Dine In",
                        desc="Experience the full sensory journey of Escale in our sun-drenched dining room.",
                        cta="RESERVE NOW",
                        route="/reservation",
                    ),
                    self._experience_card(
                        icon=ft.Icons.DELIVERY_DINING,
                        title="Fast Delivery",
                        desc="The Escale experience brought directly to your doorstep with meticulous packaging.",
                        cta="ORDER ONLINE",
                        route="/menu",
                    ),
                ],
            ),
        )

    def _experience_card(self, icon: str, title: str, desc: str, cta: str, route: str) -> ft.Control:
        return ft.Container(
            border_radius=16,
            bgcolor="white",
            padding=ft.padding.all(18),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
            on_click=lambda e: self._navigate(route),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, size=32, color="#e57722"),
                        ],
                    ),
                    ft.Text(
                        title,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#1a1a1a",
                    ),
                    ft.Text(
                        desc,
                        size=13,
                        color="#5a5249",
                        text_align=ft.TextAlign.JUSTIFY,
                    ),
                    ft.Container(height=4),
                    ft.Text(
                        cta,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color="#e57722",
                    ),
                ],
            ),
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _navigate(self, route: str) -> None:
        if self.on_navigate:
            self.on_navigate(route)

    def _load_featured_dishes(self) -> list[dict]:
        try:
            return fetch_featured_dishes("http://127.0.0.1:8000/mobile/featured-dishes/")[:3]
        except Exception:
            return []

    def _content_width(self, max_width: int) -> int | None:
        w = self.page.width
        if w and w > 0:
            return min(int(w), max_width)
        return max_width

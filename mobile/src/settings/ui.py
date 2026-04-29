from __future__ import annotations

import flet as ft


class SettingsFeature:
    def __init__(self, page: ft.Page):
        self.page = page

        self.notifications_switch = ft.Switch(value=True, active_color="#FF5C00")
        self.location_switch = ft.Switch(value=True, active_color="#FF5C00")
        self.marketing_switch = ft.Switch(value=False, active_color="#FF5C00")

    def build_view(self) -> ft.Control:
        return ft.Container(
            expand=True,
            bgcolor="#f5efe1",
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
                controls=[
                    ft.Container(height=12),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=20),
                        content=ft.Text("App Settings", size=34, weight=ft.FontWeight.BOLD, color="#2f2a24"),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=20),
                        content=ft.Text("Customize how Escale works for you.", size=14, color="#6a6155"),
                    ),
                    self._settings_card(
                        title="Notifications",
                        subtitle="Get updates for orders, reservations and promotions.",
                        trailing=self.notifications_switch,
                    ),
                    self._settings_card(
                        title="Location Access",
                        subtitle="Enable location for faster delivery address suggestions.",
                        trailing=self.location_switch,
                    ),
                    self._settings_card(
                        title="Marketing Emails",
                        subtitle="Receive special offers and event announcements.",
                        trailing=self.marketing_switch,
                    ),
                    self._settings_row("Language", "English"),
                    self._settings_row("Theme", "Light"),
                    self._settings_row("Privacy Policy", "View"),
                    self._settings_row("Terms & Conditions", "View"),
                    ft.Container(height=20),
                ],
            ),
        )

    def _settings_card(self, title: str, subtitle: str, trailing: ft.Control) -> ft.Control:
        return ft.Container(
            margin=ft.margin.symmetric(horizontal=16),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border_radius=14,
            bgcolor="#ffffff",
            border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color="#2f2a24"),
                                ft.Text(subtitle, size=12, color="#6a6155"),
                            ],
                        ),
                    ),
                    trailing,
                ],
            ),
        )

    def _settings_row(self, title: str, value: str) -> ft.Control:
        return ft.Container(
            margin=ft.margin.symmetric(horizontal=16),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border_radius=12,
            bgcolor="#ffffff",
            border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(title, size=14, color="#2f2a24", weight=ft.FontWeight.W_600),
                    ft.Text(value, size=13, color="#8a8278"),
                ],
            ),
        )

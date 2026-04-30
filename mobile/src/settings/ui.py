from __future__ import annotations

import flet as ft
import flet_geolocator as geolocator


class SettingsFeature:
    def __init__(
        self,
        page: ft.Page,
        notifications_enabled: bool = True,
        on_notifications_change=None,
        location_enabled: bool = False,
        on_location_change=None,
    ):
        self.page = page
        self.on_notifications_change = on_notifications_change
        self.on_location_change = on_location_change

        self.geolocator = geolocator.Geolocator()
        if self.geolocator not in self.page.services:
            self.page.services.append(self.geolocator)

        self.notifications_switch = ft.Switch(
            value=notifications_enabled,
            active_color="#FF5C00",
            on_change=self._handle_notifications_toggle,
        )
        self.location_status = ft.Text("Location is disabled.", size=12, color="#6a6155")
        self.location_switch = ft.Switch(
            value=location_enabled,
            active_color="#FF5C00",
            on_change=self._handle_location_toggle,
        )
        self.marketing_switch = ft.Switch(value=False, active_color="#FF5C00")

        if location_enabled:
            self.location_status.value = "Location enabled. Tap refresh by toggling off/on if needed."

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
                        subtitle_control=ft.Text("Get updates for orders, reservations and promotions.", size=12, color="#6a6155"),
                        trailing=self.notifications_switch,
                    ),
                    self._settings_card(
                        title="Location Access",
                        subtitle_control=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text("Enable location for faster delivery address suggestions.", size=12, color="#6a6155"),
                                self.location_status,
                            ],
                        ),
                        trailing=self.location_switch,
                    ),
                    self._settings_row("Language", "English"),
                    self._settings_row("Theme", "Light"),
                    self._settings_row("Privacy Policy", "View"),
                    self._settings_row("Terms & Conditions", "View"),
                    ft.Container(height=20),
                ],
            ),
        )

    def _handle_notifications_toggle(self, e: ft.ControlEvent) -> None:
        if callable(self.on_notifications_change):
            self.on_notifications_change(bool(self.notifications_switch.value))

    def _handle_location_toggle(self, e: ft.ControlEvent) -> None:
        self.page.run_task(self._apply_location_toggle)

    async def _apply_location_toggle(self) -> None:
        enabled = bool(self.location_switch.value)
        if not enabled:
            self.location_status.value = "Location is disabled."
            if callable(self.on_location_change):
                self.on_location_change(False)
            self.page.update()
            return

        self.location_status.value = "Requesting location permission..."
        self.page.update()

        try:
            service_enabled = await self.geolocator.is_location_service_enabled()
            if not service_enabled:
                self.location_switch.value = False
                self.location_status.value = "Device location service is off. Please turn on GPS/location services."
                if callable(self.on_location_change):
                    self.on_location_change(False)
                self.page.update()
                return

            permission_status = await self.geolocator.get_permission_status()
            permission_text = str(permission_status).upper()
            if "DENIED" in permission_text or "UNABLE" in permission_text:
                permission_status = await self.geolocator.request_permission()
                permission_text = str(permission_status).upper()

            if "DENIED_FOREVER" in permission_text or "DENIED" in permission_text:
                self.location_switch.value = False
                self.location_status.value = "Location permission denied. Please enable it in app settings."
                if callable(self.on_location_change):
                    self.on_location_change(False)
                self.page.update()
                return

            location = await self.geolocator.get_current_position()
            if not location:
                raise RuntimeError("Location unavailable")

            self.location_status.value = f"Current location: {location.latitude:.5f}, {location.longitude:.5f}"
            if callable(self.on_location_change):
                self.on_location_change(True)
        except Exception as exc:
            self.location_switch.value = False
            message = str(exc).strip()
            if not message:
                message = "Permission denied or location service unavailable"
            message_lower = message.lower()
            if "no location permissions are defined in the manifest" in message_lower:
                self.location_status.value = (
                    "Location permission missing in Android manifest for this run. Build/install Android app with location permissions enabled."
                )
            else:
                self.location_status.value = f"Location access failed: {message}"
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Location error: {message}"),
                open=True,
                bgcolor="#8b1e1e",
            )
            if callable(self.on_location_change):
                self.on_location_change(False)
        self.page.update()

    def _settings_card(self, title: str, subtitle_control: ft.Control, trailing: ft.Control) -> ft.Control:
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
                                subtitle_control,
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

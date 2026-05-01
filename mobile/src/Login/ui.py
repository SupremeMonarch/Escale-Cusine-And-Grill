import flet as ft
import json
import os
import urllib.request
import urllib.error


class LoginFeature:
    def __init__(self, page: ft.Page, on_navigate):
        self._page = page
        self.on_navigate = on_navigate

        # Simulating token storage
        self.token_storage = {}

        # Layout settings for the base Column
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.alignment = ft.MainAxisAlignment.CENTER
        self.expand = True
        self.spacing = 15

        # ---------- Header ----------
        self.header = ft.Text(
            "Sign In",
            size=28,
            weight=ft.FontWeight.BOLD
        )

        # ---------- Username ----------
        self.username_label = ft.Text("Username")

        self.username = ft.TextField(
            hint_text="Type in Username",
            width=300
        )

        # ---------- Password ----------
        self.password_label = ft.Text("Password")

        self.password = ft.TextField(
            hint_text="Type in password",
            password=True,
            can_reveal_password=True,
            width=300
        )

        # ---------- Remember / Forgot ----------
        self.remember_me = ft.Checkbox(
            value=False,
            label="Remember Me"
        )

        self.forgot_password = ft.TextButton(
            "Forgot Password?",
          
        )

        self.remember_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                self.remember_me,
                self.forgot_password
            ]
        )

        # ---------- Buttons ----------
        self.login_button = ft.Container(
            content=ft.Text("Continue", color="white"),
            alignment=ft.Alignment.CENTER,
            padding=20,
            width=300,
            bgcolor="#2e6ef7",
            border_radius=10,
            on_click=self.login_user
        )

        self.signup_button = ft.Container(
            content=ft.Text("Sign Up", color="white"),
            alignment=ft.Alignment.CENTER,
            padding=20,
            width=300,
            bgcolor="#2e6ef7",
            border_radius=10,
            on_click=lambda e: self.on_navigate("/signup")
        )

    # ---------- VIEW ----------
    def build_login_view(self):
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=30,     
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
                controls=[
                    self.header,
                    self.username_label,
                    self.username,
                    self.password_label,
                    self.password,
                    self.remember_row,
                    self.login_button,
                    self.signup_button
                ]
            )
        )

    # ---------- LOGIN ----------
    def login_user(self, e):
        base_url = os.getenv("ECAG_API_BASE_URL", "http://192.168.100.12:8000").rstrip("/")
        url = f"{base_url}/api/auth/login/"

        data = {
            "username": self.username.value,
            "password": self.password.value
        }

        try:
            payload = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                token = result.get("token")
                self.token_storage["token"] = token
                self.on_navigate("/")
        except urllib.error.HTTPError:
            self._error("Invalid credentials")
        except Exception as ex:
            self._error(f"Request failed: {str(ex)}")

    
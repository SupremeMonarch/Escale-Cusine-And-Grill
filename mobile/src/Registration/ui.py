import flet as ft
import datetime
import json
import os
import urllib.request
import urllib.error


class RegistrationFeature:
    def __init__(self, page: ft.Page, on_navigate):
        self.page = page
        self.on_navigate = on_navigate

        self.username = ft.TextField(hint_text="Username", width=300)
        self.password1 = ft.TextField(hint_text="Password", password=True, width=300)
        self.password2 = ft.TextField(hint_text="Confirm Password", password=True, width=300)

        self.email = ft.TextField(hint_text="Email", width=300)
        self.first_name = ft.TextField(hint_text="First Name", width=300)
        self.last_name = ft.TextField(hint_text="Last Name", width=300)
        self.phone_number = ft.TextField(hint_text="Phone (optional)", width=300)
        self.address = ft.TextField(hint_text="Address (optional)", width=300)

        today = datetime.datetime.now()

        self.date_of_birth = ft.TextField(
            hint_text="YYYY-MM-DD",
            read_only=True,
            width=250
        )

        self.picker = ft.DatePicker(
            first_date=datetime.datetime(year=today.year - 100, month=1, day=1),
            last_date=today,
            on_change=self.handle_change,
        )

        self.picker_button = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=self.open_picker
        )

        self.DOB_row = ft.Row(
            controls=[self.date_of_birth, self.picker_button]
        )

        self.confirm_button = ft.ElevatedButton(
            "Confirm",
            on_click=self.submit_form
        )

        self.login_button = ft.ElevatedButton(
            "Login",
            on_click=lambda e: self.on_navigate("/login")
        )

    def build_signup_view(self):
        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.Text("Sign Up", size=28, weight=ft.FontWeight.BOLD),
                self.username,
                self.password1,
                self.password2,
                self.email,
                self.first_name,
                self.last_name,
                self.phone_number,
                self.address,
                self.DOB_row,
                self.confirm_button,
                self.login_button,
            ]
        )

    def open_picker(self, e):
        self.picker.open = True
        self.page.update()

    def handle_change(self, e):
        if self.picker.value:
            self.date_of_birth.value = self.picker.value.strftime("%Y-%m-%d")
            self.page.update()

    def setup(self):
        self.page.overlay.append(self.picker)

    def submit_form(self, e):
        if self.password1.value != self.password2.value:
            self._error("Passwords do not match")
            return

        data = {
            "username": self.username.value,
            "password": self.password1.value,
            "email": self.email.value,
            "first_name": self.first_name.value,
            "last_name": self.last_name.value,
            "phone": self.phone_number.value,
            "address": self.address.value,
            "dob": self.date_of_birth.value
        }

        base_url = os.getenv("ECAG_API_BASE_URL", "http://192.168.100.12:8000").rstrip("/")
        try:
            payload = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/auth/register/",
                data=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 201:
                    self._success("Account created successfully")
                    self.on_navigate("/login")
                else:
                    self._error("Registration failed")
        except urllib.error.HTTPError as e:
            self._error(e.read().decode("utf-8", errors="ignore") or str(e))
        except Exception as e:
            self._error(str(e))

    def _error(self, msg):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="red")
        self.page.snack_bar.open = True
        self.page.update()

    def _success(self, msg):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()
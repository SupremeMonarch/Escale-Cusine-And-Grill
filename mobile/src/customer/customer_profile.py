import flet as ft
from utils.dashboard_api import fetch_profile, save_profile
from utils.dashboard_utils import (
    COLORS, FONT_FAMILY, FONT_URL,
    build_theme, empty_state, loading_spinner,
    primary_button, secondary_button,
)

class ProfileInfoField(ft.Container):
    def __init__(self, label: str, value: str, expand=False):
        super().__init__()
        self.expand        = expand
        self.bgcolor       = COLORS["surface_container_low"]
        self.padding       = 16
        self.border_radius = 16
        self.width         = float("inf")
        self.content       = ft.Column(
            spacing=4,
            controls=[
                ft.Text(
                    label.upper(),
                    size=9,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["on_surface_variant"], opacity=0.7,
                ),
                ft.Text(
                    value or "",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=COLORS["on_surface"],
                ),
            ],
        )

class ProfileEditField(ft.Container):
    def __init__(self, label: str, value: str, expand=False, keyboard_type=ft.KeyboardType.TEXT, password=False):
        super().__init__()
        self.expand        = expand
        self.bgcolor       = COLORS["surface_container_lowest"]
        self.padding       = ft.Padding.only(left=16, right=12, top=10, bottom=10)
        self.border_radius = 16
        self.border        = ft.Border.all(1, COLORS["card_outline"])
        self.width         = float("inf")

        self.field = ft.TextField(
            value=value or "",
            label=label.upper(),
            label_style=ft.TextStyle(
                size=11,
                weight=ft.FontWeight.BOLD,
                color=COLORS["on_surface_variant"],
            ),
            text_style=ft.TextStyle(
                size=14,
                weight=ft.FontWeight.W_600,
                color=COLORS["on_surface"],
            ),
            border=ft.InputBorder.NONE,
            keyboard_type=keyboard_type,
            password=password,

            cursor_color=COLORS["primary"],
        )
        self.content = self.field

    @property
    def value(self) -> str:
        return self.field.value or ""

def get_profile_view(page: ft.Page, navigate_to=None):
    token      = page.session.store.get("token")
    user_data: list[dict] = [{}]
    is_editing: list[bool] = [False]

    content_col = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO)

    save_btn_text = ft.Text(
        "Save Changes", color=COLORS["white"],
        weight=ft.FontWeight.BOLD, size=14,
    )
    save_loading = ft.ProgressRing(
        color=COLORS["white"], width=18, height=18, visible=False,
    )
    save_btn = ft.Container(
        content=ft.Row(
            [save_loading, save_btn_text],
            alignment=ft.MainAxisAlignment.CENTER, spacing=10,
        ),
        bgcolor=COLORS["primary"],
        padding=ft.Padding.symmetric(vertical=12),
        border_radius=100,
        visible=False,
    )

    # Edit and Cancel
    edit_btn   = primary_button("Edit Profile Details", icon=ft.Icons.EDIT)
    cancel_btn = secondary_button("Cancel")
    cancel_btn.visible = False
    save_btn.visible   = False

    edit_fields: dict[str, ProfileEditField] = {}

    # --- Feedback snackbar ---
    def show_feedback(message: str, is_error=False):
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    message,
                    size=13,
                    color=COLORS["error"] if is_error else COLORS["on_surface"],
                ),
                bgcolor=COLORS["error_bg"] if is_error else COLORS["surface_container_low"],
                duration=3000,
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        )
        page.update()

    # --- Section ---
    def section(title: str, fields: list) -> ft.Column:
        return ft.Column([
            ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=COLORS["on_surface"]),
            ft.Column(fields, spacing=12),
        ], spacing=16)

    def build_read_view(u: dict) -> list:
        p         = u.get("profile") or {}
        full_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or "—"
        return [
            section("Basic Information", [
                ProfileInfoField("Full Name",     full_name),
                ProfileInfoField("Username",      u.get("username", "—")),
                ProfileInfoField("Email Address", u.get("email", "—")),
                ProfileInfoField("Phone Number",  p.get("phone_number") or "----------"),
            ]),
            section("Address & Details", [
                ProfileInfoField("Address",       p.get("address") or "----------"),
                ProfileInfoField("Date of Birth", p.get("date_of_birth") or "----------"),
            ]),
        ]

    def build_edit_view(u: dict) -> list:
        p = u.get("profile") or {}
        edit_fields.clear()

        def editfield(key, label, value, **kwargs) -> ProfileEditField:
            f = ProfileEditField(label, value, **kwargs)
            edit_fields[key] = f
            return f

        return [
            section("Basic Information", [
                ft.Row([
                    editfield("first_name", "First Name", u.get("first_name", ""), expand=True),
                    editfield("last_name",  "Last Name",  u.get("last_name",  ""), expand=True),
                ], spacing=12),
                editfield("email", "Email Address", u.get("email", ""),
                   keyboard_type=ft.KeyboardType.EMAIL),
                editfield("phone_number", "Phone Number", p.get("phone_number") or "",
                   keyboard_type=ft.KeyboardType.PHONE),
            ]),
            section("Address & Details", [
                editfield("address",       "Address",                  p.get("address") or ""),
                editfield("date_of_birth", "Date of Birth (YYYY-MM-DD)", p.get("date_of_birth") or ""),
            ]),
        ]

    def render_view():
        if is_editing[0]:
            sections           = build_edit_view(user_data[0])
            edit_btn.visible   = False
            save_btn.visible   = True
            cancel_btn.visible = True
        else:
            sections           = build_read_view(user_data[0])
            edit_btn.visible   = True
            save_btn.visible   = False
            cancel_btn.visible = False

        content_col.controls = sections + [
            save_btn, cancel_btn, edit_btn, ft.Container(height=40),
        ]
        page.update()

    # --- Event handlers ---
    def on_edit(_):
        is_editing[0] = True
        render_view()

    def on_cancel(_):
        is_editing[0] = False
        render_view()

    def on_save(_):
        page.run_task(_do_save)

    async def _do_save():
        save_btn_text.visible = False
        save_loading.visible  = True
        page.update()

        u   = user_data[0]
        uid = u.get("id")

        def _val(key) -> str:
            return edit_fields.get(key, ProfileEditField("", "")).value

        user_payload = {
            "first_name": _val("first_name"),
            "last_name":  _val("last_name"),
            "email":      _val("email"),
        }
        profile_payload = {
            "phone_number":  _val("phone_number"),
            "address":       _val("address"),
            "date_of_birth": _val("date_of_birth") or None,
        }

        ok, err = await save_profile(token, uid, user_payload, profile_payload)

        save_btn_text.visible = True
        save_loading.visible  = False

        if ok:
            u.update(user_payload)
            u.setdefault("profile", {}).update(
                {k: v for k, v in profile_payload.items() if v}
            )
            is_editing[0] = False
            render_view()
            show_feedback("Profile updated successfully.")
        else:
            show_feedback(err or "Failed to save. Please try again.", is_error=True)
            page.update()

    edit_btn.on_click   = on_edit
    save_btn.on_click   = on_save
    cancel_btn.on_click = on_cancel

    # --- Initial loading state ---
    loading_col = ft.Column([loading_spinner()])

    main_content = ft.Column(
        [
            ft.Column([
                ft.Text("My Profile", size=24, weight=ft.FontWeight.W_800,
                        color=COLORS["on_surface"]),
                ft.Text("Manage your account details and preferences",
                        size=14, color=COLORS["on_surface_variant"]),
            ], spacing=4),
            ft.Divider(height=1, color=ft.Colors.TRANSPARENT),
            loading_col,
        ],
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
    )

    async def load_profile():
        data = await fetch_profile(token)
        if not data:
            loading_col.controls = [
                empty_state(
                    "Couldn't load profile.\nCheck your connection.",
                    ft.Icons.PERSON_OFF_OUTLINED,
                )
            ]
            page.update()
            return

        user_data[0] = data
        main_content.controls[2] = content_col
        render_view()

    page.run_task(load_profile)

    return ft.Column([
        ft.Container(
            content=main_content,
            padding=ft.Padding.only(left=24, right=24, top=16, bottom=24),
            expand=True,
        )
    ], scroll=ft.ScrollMode.AUTO, expand=True)

if __name__ == "__main__":
    async def main(page: ft.Page):
        page.title   = "Escale - My Profile"
        page.bgcolor = COLORS["background"]
        page.padding = 0
        page.fonts   = {FONT_FAMILY: FONT_URL}
        page.theme   = build_theme()

        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.MENU, icon_color=COLORS["primary"]),
                    ft.Text("Escale", size=24, weight=ft.FontWeight.BOLD,
                            color=COLORS["on_surface"]),
                ]),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON), radius=20),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding.only(left=24, right=24, top=10, bottom=10),
            bgcolor=COLORS["background"],
        )
        page.add(ft.Column([header, get_profile_view(page)], spacing=0, expand=True))

    ft.app(main)

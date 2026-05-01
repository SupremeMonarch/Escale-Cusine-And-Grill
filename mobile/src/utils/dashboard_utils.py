import flet as ft

COLORS = {
    "primary":                  "#9e3c00",
    "background":               "#fff4f0",

    "surface":                  "#ffffff",
    "surface_container_lowest": "#fff9f6",
    "surface_container_low":    "#ffede4",
    "surface_container":        "#ffdcc7",
    "surface_container_high":   "#ffdcc7",

    "on_surface":               "#4a2507",
    "on_surface_variant":       "#805030",

    "secondary_container":      "#ffc696",
    "on_secondary_container":   "#6d3b00",
    "tertiary_container":       "#f7ad1e",
    "on_tertiary_container":    "#4e3300",

    "outline":                  "#dca079",
    "card_outline":             "#f0d5c3",
    "card_divider":             "#f5e1d5",

    "error":                    "#b91c1c",
    "error_bg":                 "#fee2e2",
    "white":                    "#ffffff",

    "indicator":                "#ffdcc7",
}

FONT_FAMILY = "Plus Jakarta Sans"
FONT_URL    = (
    "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans"
    ":wght@400;500;600;700;800&display=swap"
)

def build_theme() -> ft.Theme:
    return ft.Theme(font_family=FONT_FAMILY)

def filter_chip(label: str, is_active: bool, on_click=None) -> ft.Container:
    """Pill-shaped filter chip for Orders / Reservations screens."""
    return ft.Container(
        content=ft.Text(
            label, size=13,
            weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_600,
            color=COLORS["white"] if is_active else COLORS["on_surface_variant"],
        ),
        bgcolor=COLORS["primary"] if is_active else COLORS["surface_container_low"],
        padding=ft.Padding.symmetric(horizontal=20, vertical=5),
        border_radius=10,
        animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
        data=label,
        on_click=on_click,
        shadow=ft.BoxShadow(
            offset=ft.Offset(0, 1),
            spread_radius=0,
            blur_radius=1,
            color=ft.Colors.with_opacity(0.3, COLORS["on_surface"]),
        )
    )


def stat_card(icon, label: str, count_ref: ft.Ref, bg1: str, bg2: str, color: str) -> ft.Container:
    """Overview screen stat card (active deliveries, upcoming bookings)."""
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(icon, color=color, size=20),
                ft.Text(label, size=9, weight=ft.FontWeight.BOLD, color=color, opacity=0.8),
            ], spacing=6),
            ft.Text("—", size=28, weight=ft.FontWeight.W_800, color=color, ref=count_ref),
        ], spacing=4),

        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[bg1, bg2]),
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        border_radius=16,
        border=ft.Border.all(1, COLORS["card_outline"]),
        expand=True,
        shadow=ft.BoxShadow(
            offset=ft.Offset(0, 2),
            spread_radius=0,
            blur_radius=2,
            color=ft.Colors.with_opacity(0.3, COLORS["on_surface"]),
        )
    )

def empty_state(message: str, icon=ft.Icons.RECEIPT_LONG_OUTLINED) -> ft.Container:
    """Centred empty-state placeholder used across list screens."""
    return ft.Container(
        content=ft.Column([
            ft.Icon(icon, size=48, color=COLORS["on_surface_variant"]),
            ft.Text(
                message,
                color=COLORS["on_surface_variant"],
                text_align=ft.TextAlign.CENTER,
                size=14,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        bgcolor=COLORS["surface_container_low"],
        padding=40,
        border_radius=20,
        alignment=ft.alignment.Alignment(0,0),
        border=ft.Border.all(1, COLORS["card_outline"]),
        shadow=ft.BoxShadow(
            offset=ft.Offset(0, 2),
            spread_radius=0,
            blur_radius=2,
            color=ft.Colors.with_opacity(0.2, COLORS["on_surface"]),
        )
    )


def loading_spinner() -> ft.Container:
    """Centered loading spinner for initial data fetch states."""
    return ft.Container(
        content=ft.ProgressRing(color=COLORS["primary"]),
        alignment=ft.alignment.Alignment(0,0),
        padding=40,
    )


def primary_button(label: str, icon=None, on_click=None) -> ft.Container:
    row_children = []
    if icon:
        row_children.append(ft.Icon(icon, color=COLORS["white"], size=18))
    row_children.append(
        ft.Text(label, color=COLORS["white"], weight=ft.FontWeight.BOLD, size=14)
    )
    return ft.Container(
        content=ft.Row(row_children, alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        bgcolor=COLORS["primary"],
        padding=ft.Padding.symmetric(vertical=12),
        border_radius=100,
        on_click=on_click,
    )


def secondary_button(label: str, icon=None, on_click=None) -> ft.Container:
    row_children = []
    if icon:
        row_children.append(ft.Icon(icon, color=COLORS["on_surface_variant"], size=18))
    row_children.append(
        ft.Text(label, color=COLORS["on_surface_variant"], weight=ft.FontWeight.BOLD, size=14)
    )
    return ft.Container(
        content=ft.Row(row_children, alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        bgcolor=COLORS["surface_container_low"],
        padding=ft.Padding.symmetric(vertical=12),
        border_radius=100,
        border=ft.Border.all(1, COLORS["card_outline"]),
        on_click=on_click,
    )

ORDER_TYPE = {
    "dine in":  {"bg": "#e0f2fe", "text": "#0369a1", "label": "DINE-IN"},
    "delivery": {"bg": "#ede9fe", "text": "#6d28d9", "label": "DELIVERY"},
    "pick up":  {"bg": "#fef9c3", "text": "#854d0e", "label": "TAKEOUT"},
}

DINE_IN = {
    "in_progress": ("IN PROGRESS", "#ffd4bb", "#9e3c00"),
    "completed":   ("COMPLETED",   "#d1fae5", "#065f46"),
}

DELIVERY = {
    "preparing_order": ("PREPARING",        "#ffd4bb", "#9e3c00"),
    "in_progress":     ("OUT FOR DELIVERY",  "#fef3c7", "#92400e"),
    "delivered":       ("DELIVERED",         "#d1fae5", "#065f46"),
}

TAKEOUT = {
    "preparing_order":  ("PREPARING",        "#ffd4bb", "#9e3c00"),
    "ready_for_pickup": ("READY FOR PICKUP", "#fef3c7", "#92400e"),
    "picked_up":        ("PICKED UP",        "#d1fae5", "#065f46"),
}

def order_type_badge(order_type: str) -> ft.Container:
    cfg = ORDER_TYPE.get(
        order_type.lower(),
        {"bg": "#f3f4f6", "text": "#374151", "label": order_type.upper()},
    )
    return ft.Container(
        content=ft.Text(cfg["label"], size=9, weight=ft.FontWeight.BOLD, color=cfg["text"]),
        bgcolor=cfg["bg"],
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=6,
    )

def get_order_status_colours(order: dict) -> tuple[str, str, str]:
    order_type = order.get("order_type", "").lower()
    if order_type == "dine in":
        ord = order.get("status", "in_progress")
        return DINE_IN.get(ord, DINE_IN["in_progress"])
    if order_type == "delivery":
        ds = (order.get("delivery") or {}).get("delivery_status", "preparing_order")
        return DELIVERY.get(ds, DELIVERY["preparing_order"])
    if order_type == "pick up":
        ps = (order.get("takeout") or {}).get("pickup_status", "preparing_order")
        return TAKEOUT.get(ps, TAKEOUT["preparing_order"])
    return DINE_IN["in_progress"]


RESERVATION_STATUS = {
    "pending":   {"bg": "#fef3c7", "text": "#92400e"},
    "confirmed": {"bg": "#ffc696", "text": "#6d3b00"},
    "seated":    {"bg": "#dbeafe", "text": "#1e40af"},
    "completed": {"bg": "#d1fae5", "text": "#065f46"},
    "cancelled": {"bg": "#fee2e2", "text": "#991b1b"},
    "no-show":   {"bg": "#f3f4f6", "text": "#4b5563"},
    "fallback":  {"bg": "#fef3c7", "text": "#92400e"},
}

NON_CANCELLABLE_STATUSES = {"completed", "cancelled", "no-show", "seated"}

def get_res_status_colours(status: str) -> tuple[str, str]:
    s = RESERVATION_STATUS.get(status.lower(), RESERVATION_STATUS["fallback"])
    return s["bg"], s["text"]


def status_badge(label: str, bg: str, text_color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, size=9, weight=ft.FontWeight.BOLD, color=text_color),
        bgcolor=bg,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=6,
    )

def get_item_name(item) -> str:
    if isinstance(item, dict):
        return item.get("name", item.get("item", "Unknown"))
    return str(item) if item else "Unknown"


from datetime import datetime, date
def format_order_date(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        diff = (date.today() - dt.date()).days
        time_str = dt.strftime("%I:%M %p").lstrip("0")
        if diff == 0:
            return f"Today, {time_str}"
        elif diff == 1:
            return f"Yesterday, {time_str}"
        return dt.strftime("%b %d, %I:%M %p").lstrip("0")
    except Exception:
        return dt_str

def format_res_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        diff = (date.today() - dt.date()).days
        if diff == 0:
            return "Today"
        return dt.strftime("%b %d, %Y")
    except Exception:
        return date_str

def format_res_time(time_str: str) -> str:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).strftime("%I:%M %p").lstrip("0")
        except Exception:
            continue
    return time_str

def is_today(dt_str: str) -> bool:
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.date() == date.today()
    except Exception:
        return False

def is_today_or_future_date(date_str: str) -> bool:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        return dt >= date.today()
    except Exception:
        return False

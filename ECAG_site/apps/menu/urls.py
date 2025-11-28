from django.urls import path
from . import views

app_name = "menu"

urlpatterns = [
    # /menu/           → we can show starters by default
    path("", views.menu_starters, name="menu_home"),

    # /menu/starters/  → Starters page
    path("starters/", views.menu_starters, name="menu_starters"),

    # /menu/main-course/ → Main Course page
    path("main-course/", views.menu_main_course, name="menu_main_course"),

    # /menu/beverages/ → Beverages page
    path("beverages/", views.menu_beverages, name="menu_beverages"),
    # Checkout page
    path("checkout/", views.checkout, name="checkout"),
    path("save_cart/", views.save_cart, name="save_cart"),
    path("checkout/success/", views.checkout_success, name="checkout_success"),
]

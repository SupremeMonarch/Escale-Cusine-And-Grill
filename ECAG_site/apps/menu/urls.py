# menu/urls.py
from django.urls import path
from . import views

app_name = "menu"   # 👈 this is what provides the namespace

urlpatterns = [
    path("", views.menu, name="list"),
]

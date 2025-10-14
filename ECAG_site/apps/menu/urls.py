# menu/urls.py
from django.urls import path
from . import views

app_name = "menu"   # 👈 this is what provides the namespace

urlpatterns = [
    path("", views.menu_starters, name='menu_starters'),
    path('main-course/', views.menu_main_course, name='menu_main_course'),
    path('beverages/', views.menu_beverages, name='menu_beverages'),
]


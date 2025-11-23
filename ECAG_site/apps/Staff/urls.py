from django.urls import path
from . import views

urlpatterns = [
    path('', views.staff_overview, name='staff_overview'),
    path('overview/', views.staff_overview, name='staff_overview'),
    path('orders/', views.staff_orders, name='staff_orders'),
    path('reservations/', views.staff_reservations, name='staff_reservations'),
]

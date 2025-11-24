from django.urls import path
from . import views

urlpatterns = [
    path('', views.staff_overview, name='staff_overview'),
    path('overview/', views.staff_overview, name='staff_overview'),
    path('orders/', views.staff_orders, name='staff_orders'),
    path('reservations/', views.staff_reservations, name='staff_reservations'),
    path('orders/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('reservations/update-status/<int:reservation_id>/', views.update_reservation_status, name='update_reservation_status'),
]

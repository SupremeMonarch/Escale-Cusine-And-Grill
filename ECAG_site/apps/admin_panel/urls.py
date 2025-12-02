from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='admin-overview'),
    path('orders/', views.orders, name='admin-orders'),
    path('reservations/', views.reservations, name='admin-reservations'),
    path('menu/', views.menu, name='admin-menu'),
    path('customers/', views.customers, name='admin-customers'),
    path('staffs/', views.staffs, name='admin-staffs'),
    path('reviews/', views.reviews, name='admin-reviews'),
    path('orders/<int:order_id>/', views.order_detail, name='admin-order-detail'),
    path('orders/<int:order_id>/next-status/', views.order_next_status, name='admin-order-next-status'),
    path('orders/<int:order_id>/cancel/', views.order_cancel, name='admin-order-cancel'),
    path("reservations/<int:reservation_id>/action/", views.reservation_action, name="admin-reservation-action"),
    path("invite-staff/", views.invite_staff, name="admin-invite-staff"),
    path('review-detail/<int:review_id>/', views.review_detail, name='review-detail'),
    path('export/orders/', views.export_orders, name='export_orders'),
    path('export/reservations/', views.export_reservations, name='export_reservations'),
    path('export/reviews/', views.export_reviews, name='export_reviews'),
]

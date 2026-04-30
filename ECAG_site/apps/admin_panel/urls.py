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

    # Mobile admin JSON endpoints
    path('mobile/overview/', views.mobile_overview_data, name='admin-mobile-overview'),
    path('mobile/orders/', views.mobile_orders_data, name='admin-mobile-orders'),
    path('mobile/orders/<int:order_id>/action/', views.mobile_order_action, name='admin-mobile-order-action'),
    path('mobile/reservations/', views.mobile_reservations_data, name='admin-mobile-reservations'),
    path('mobile/reservations/<int:reservation_id>/action/', views.mobile_reservation_action, name='admin-mobile-reservation-action'),
    path('mobile/menu/', views.mobile_menu_data, name='admin-mobile-menu'),
    path('mobile/customers/', views.mobile_customers_data, name='admin-mobile-customers'),
    path('mobile/staffs/', views.mobile_staffs_data, name='admin-mobile-staffs'),
    path('mobile/staffs/invite/', views.mobile_invite_staff, name='admin-mobile-invite-staff'),
    path('mobile/reviews/', views.mobile_reviews_data, name='admin-mobile-reviews'),
    path('mobile/reviews/<int:review_id>/action/', views.mobile_review_action, name='admin-mobile-review-action'),
]

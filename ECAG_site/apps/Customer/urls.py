from django.urls import path
from . import views

urlpatterns = [
    # The name parameter is used in templates for URL reversing (e.g., {% url 'overview' %})
    path('', views.overview, name='overview'),
    path('overview/', views.overview, name='overview'),
    path('my_orders/', views.my_orders, name='my_orders'),
    path('my_reservations/', views.my_reservations, name='my_reservations'),
    path('profile/', views.profile, name='profile'),
]

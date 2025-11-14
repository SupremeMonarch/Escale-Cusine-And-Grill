from django.urls import path
from . import views

urlpatterns = [
    # The name parameter is used in templates for URL reversing (e.g., {% url 'overview' %})
    path('', views.overview, name='overview'),
    path('overview/', views.overview, name='overview'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('profile/', views.profile, name='profile'),
]

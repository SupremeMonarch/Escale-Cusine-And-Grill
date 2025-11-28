from django.urls import path
from . import views

urlpatterns = [
    path('home/',views.home),
    path('contact/', views.contact),
    path('inheritor_test/', views.inheritor),
    path('login/',views.login_view, name="login"),
    
    ]
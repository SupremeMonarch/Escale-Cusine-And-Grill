from django.urls import path
from . import views

app_name='login_registration'

urlpatterns = [
    path('register/',views.register,name="register"), # registration_view
    path('',views.login_view, name="login"),
    
    ]
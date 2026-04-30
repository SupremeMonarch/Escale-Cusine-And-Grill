from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="home"),      # homepage
    path("mobile/featured-dishes/", views.mobile_featured_dishes, name="mobile_featured_dishes"),
    path("mobile/notifications/", views.mobile_notifications, name="mobile_notifications"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact")
]
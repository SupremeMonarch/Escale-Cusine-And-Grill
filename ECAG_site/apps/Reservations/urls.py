from django.urls import path
from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.reservations, name="reservations"),
    path("step2/", views.reservations_step2, name="reservations_step2"),
    path("step3/", views.reservations_step3, name="reservations_step3"),
    path("review/", views.review, name="review"),
]
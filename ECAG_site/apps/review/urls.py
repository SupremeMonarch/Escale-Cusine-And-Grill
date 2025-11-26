from django.urls import path
from . import views

app_name = 'review'

urlpatterns = [
    path('', views.review, name='review'),
    path('step2/', views.review_step2, name='review_step2'),
    path('helpful/<int:pk>/', views.review_helpful, name='review_helpful'),
    path('verify/<int:pk>/', views.review_verify, name='review_verify'),
]
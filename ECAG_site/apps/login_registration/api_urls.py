from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = router.urls + [
    path('login/', obtain_auth_token),
    path('register/', views.RegisterAPIView.as_view()),
]

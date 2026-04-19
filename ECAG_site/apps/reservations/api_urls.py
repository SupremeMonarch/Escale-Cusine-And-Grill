from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tables', views.TableViewSet)
router.register(r'bookings', views.ReservationViewSet, basename='reservation')

urlpatterns = router.urls

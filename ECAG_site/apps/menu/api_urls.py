from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.MenuCategoryViewSet)
router.register(r'subcategories', views.MenuSubCategoryViewSet)
router.register(r'items', views.MenuItemViewSet)
router.register(r'promotions', views.PromotionViewSet)
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-items', views.OrderItemViewSet, basename='orderitem')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'deliveries', views.DeliveryViewSet, basename='delivery')
router.register(r'takeouts', views.TakeoutViewSet, basename='takeout')

urlpatterns = router.urls

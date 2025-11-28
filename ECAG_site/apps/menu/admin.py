from django.contrib import admin
from .models import (
    MenuCategory,
    MenuSubCategory,
    MenuItem,
    Promotion,
    Order,
    OrderItem,
    Delivery,
    Takeout,
    Transaction,
)

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    # your model has "category" (and slug if you added it)
    list_display = ("category",)  # or ("category", "slug") if slug exists


@admin.register(MenuSubCategory)
class MenuSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("subcategory", "category_id")
    list_filter = ("category_id",)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    # show name, subcategory and price
    list_display = ("name", "subcategory_id", "price", "is_available")
    # filter by category (through the FK) and subcategory
    list_filter = ("subcategory_id__category_id", "subcategory_id")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "item", "start_date", "end_date", "discountpercent")
    list_filter = ("start_date", "end_date")
    search_fields = ("title", "item__name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id_str", "user", "order_type", "status", "subtotal", "total", "order_date")
    list_filter = ("status", "order_type", "order_date")
    search_fields = ("order_id_str", "user__username")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "item", "quantity", "price", "subtotal")
    list_filter = ("order__status", "item__subcategory_id")
    search_fields = ("order__order_id_str", "item__name")


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("order", "address", "fee", "delivery_status", "arrival_time")
    list_filter = ("delivery_status",)
    search_fields = ("order__order_id_str", "address")


@admin.register(Takeout)
class TakeoutAdmin(admin.ModelAdmin):
    list_display = ("order", "fee")
    search_fields = ("order__order_id_str",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "payment_method", "status", "transaction_date")
    list_filter = ("payment_method", "status", "transaction_date")
    search_fields = ("order__order_id_str",)

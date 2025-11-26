from django.contrib import admin
from .models import MenuCategory, MenuSubCategory, MenuItem

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

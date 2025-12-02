from django.contrib import admin

# Register your models here.
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'date_joined','address')
    search_fields = ('first_Name', 'last_Name', 'email', 'phone_number')
    list_filter = ('date_joined','customer_id')
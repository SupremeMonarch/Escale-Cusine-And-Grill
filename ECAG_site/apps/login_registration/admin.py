from django.contrib import admin

# Register your models here.
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'First_Name', 'Last_Name', 'email', 'phone_number', 'role', 'date_joined')
    search_fields = ('First_Name', 'Last_Name', 'email', 'phone_number')
    list_filter = ('role', 'Preferences')
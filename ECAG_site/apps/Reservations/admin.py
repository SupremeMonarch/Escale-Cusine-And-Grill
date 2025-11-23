from django.contrib import admin
from .models import Reservation, Table


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
	list_display = ('reservation_id', 'date', 'time', 'guest_count', 'table_id', 'full_name', 'phone', 'email', 'status', 'created_at')
	list_filter = ('status', 'date', 'table_id')
	search_fields = ('full_name', 'phone', 'email', 'reservation_id')
	ordering = ('-date', '-time')
	readonly_fields = ('created_at',)


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
	list_display = ('table_id', 'table_number', 'seats', 'x_position', 'y_position')
	ordering = ('table_number',)


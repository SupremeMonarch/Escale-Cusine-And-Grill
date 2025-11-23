from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
	"""Admin display for reviews."""
	list_display = ('review_id', 'user_name', 'rating', 'review_title', 'submission_date', 'would_you_recommend', 'helpful_count', 'is_verified')
	list_filter = ('rating', 'would_you_recommend', 'submission_date', 'is_verified')
	search_fields = ('user_name', 'email', 'review_title', 'review_text', 'dishes_ordered')
	ordering = ('-submission_date',)
	readonly_fields = ('review_id', 'submission_date')

	# Allow toggling `is_verified` directly from the list view
	list_editable = ('is_verified',)

	def mark_verified(self, request, queryset):
		"""Admin action: mark selected reviews as verified."""
		updated = queryset.update(is_verified=True)
		self.message_user(request, f"{updated} review(s) marked as verified.")

	def mark_unverified(self, request, queryset):
		"""Admin action: mark selected reviews as not verified."""
		updated = queryset.update(is_verified=False)
		self.message_user(request, f"{updated} review(s) marked as not verified.")

	actions = ('mark_verified', 'mark_unverified')

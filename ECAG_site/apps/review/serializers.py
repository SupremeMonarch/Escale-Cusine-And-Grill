from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "review_id",
            "user_name",
            "email",
            "review_title",
            "review_text",
            "rating",
            "dishes_ordered",
            "date_of_visit",
            "submission_date",
            "would_you_recommend",
            "helpful_count",
            "is_verified",
        ]
        read_only_fields = ["review_id", "submission_date", "helpful_count", "is_verified"]

    def validate_user_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("User name is required.")
        return value

    def validate_review_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Review title is required.")
        return value

    def validate_review_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Review text is required.")
        if len(value) > 500:
            raise serializers.ValidationError("Review text must be at most 500 characters.")
        return value

    def validate_dishes_ordered(self, value):
        return value.strip()

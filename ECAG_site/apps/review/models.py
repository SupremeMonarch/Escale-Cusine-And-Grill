from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg


class Review(models.Model):
    RATING_CHOICES = [(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')]
    WOULD_YOU_RECOMMEND_CHOICES = [('yes', 'Yes, absolutely!'), ('neutral', 'Not sure / Neutral'), ('no', 'No')]

    # primary key AutoField does not accept max_length; keep default behavior
    review_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    review_title = models.CharField(max_length=100)
    review_text = models.TextField(max_length=500)
    rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    dishes_ordered = models.CharField(max_length=255, blank=True)
    date_of_visit = models.DateField(null=True, blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    would_you_recommend = models.CharField(max_length=10, choices=WOULD_YOU_RECOMMEND_CHOICES, default='neutral')
    helpful_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Review {self.review_id} by {self.user_name} (rating {self.rating})"

    def update_review(self, new_rating=None, new_text=None):
        """Safely update rating and/or review text."""
        if new_rating is not None:
            self.rating = new_rating
        if new_text is not None:
            self.review_text = new_text
        self.save()

    @classmethod
    def average_rating(cls):
        """Return the average rating across all reviews (float) or 0.0 if none."""
        result = cls.objects.aggregate(avg=Avg('rating'))
        return result['avg'] or 0.0
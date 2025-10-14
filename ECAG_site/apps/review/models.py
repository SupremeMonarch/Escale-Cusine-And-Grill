from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    RATING_CHOICES = [(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')]
    review_id = models.AutoField(max_length=10, unique=True, primary_key=True)
    user_id = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.review_id} by User {self.user_id} with Rating {self.rating}"
    
    def edit_review(self, new_rating, new_comment):
        self.rating = new_rating
        self.comment = new_comment
        self.save()

    def calculate_rating_average(user):
        reviews = Review.objects.filter(user_id=user)
        if reviews.exists():
            total_rating = sum(review.rating for review in reviews)
            return total_rating / reviews.count()
        return 0.0
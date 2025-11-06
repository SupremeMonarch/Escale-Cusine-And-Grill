from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    RATING_CHOICES = [(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')]
    WOULD_YOU_RECOMMEND_CHOICES = [('yes', 'Yes, absolutely!'), ('neutral', 'Not sure / Neutral'), ('no', 'No')]
    review_id = models.AutoField(max_length=10, unique=True, primary_key=True)
    user_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    review_title = models.CharField(max_length=100)
    review_text = models.TextField(max_length=500)
    rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    dishes_ordered = models.CharField(max_length=255)
    date_of_visit = models.DateField()
    submission_date = models.DateTimeField(auto_now_add=True)
    would_you_recommend = models.CharField(max_length=10, choices=WOULD_YOU_RECOMMEND_CHOICES)

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
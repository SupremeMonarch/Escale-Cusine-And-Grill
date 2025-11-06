from django import forms
from . import models

class ReviewForm(forms.ModelForm):
    class Meta:
        model = models.Review
        fields = ['user_name', 'email', 'review_title', 'review_text', 'rating', 'dishes_ordered', 'date_of_visit', 'would_you_recommend']
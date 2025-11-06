from django.shortcuts import render
from . import forms

# Create your views here.
def review(request):
    return render(request, 'review/review.html')

def review_step2(request):
    return render(request, 'review/review_step2.html')
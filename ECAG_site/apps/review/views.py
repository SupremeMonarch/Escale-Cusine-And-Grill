from django.shortcuts import render, redirect
from . import forms


# Create your views here.
def review(request):
    return render(request, 'review/review.html')


def review_step2(request):
    """Display and process the Review form (step 2).

    GET: show the form
    POST: validate and save, then redirect to the main review page
    """
    if request.method == 'POST':
        form = forms.ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('review:review')
    else:
        form = forms.ReviewForm()

    return render(request, 'review/review_step2.html', {'form': form})
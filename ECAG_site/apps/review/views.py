from django.shortcuts import render, redirect
from django.db.models import Avg, Count
from . import forms
from .models import Review
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.db.models import F, Sum
from django.middleware.csrf import get_token


# Create your views here.
def review(request):
    """Landing page: show aggregated review stats and recent reviews."""
    # Ensure CSRF cookie is set so client-side JS can read it for POSTs
    get_token(request)
    # base queryset
    reviews = Review.objects.all()

    # total helpful across all reviews (site-wide)
    total_helpful_agg = Review.objects.aggregate(total_helpful=Sum('helpful_count'))
    total_helpful = total_helpful_agg.get('total_helpful') or 0

    # verified reviews: count reviews admins marked as verified
    verified_count = reviews.filter(is_verified=True).count()

    # read filters/sort from query params
    sort = request.GET.get('sort', 'newest')
    rating_filter = request.GET.get('rating', 'all')

    # apply rating filter if numeric
    try:
        if rating_filter is not None and rating_filter.isdigit():
            reviews = reviews.filter(rating=int(rating_filter))
    except ValueError:
        pass

    # apply sorting
    if sort == 'newest':
        reviews = reviews.order_by('-submission_date')
    elif sort == 'oldest':
        reviews = reviews.order_by('submission_date')
    elif sort == 'highest':
        reviews = reviews.order_by('-rating', '-submission_date')
    elif sort == 'lowest':
        reviews = reviews.order_by('rating', '-submission_date')
    else:
        reviews = reviews.order_by('-submission_date')

    # average rating (float) and total count
    agg = reviews.aggregate(avg_rating=Avg('rating'), total=Count('pk'))
    average_rating = agg.get('avg_rating') or 0.0
    total_reviews = agg.get('total') or 0

    # distribution counts for 1..5
    dist_qs = reviews.values('rating').annotate(count=Count('rating'))
    distribution = {i: 0 for i in range(1, 6)}
    for row in dist_qs:
        rating = int(row['rating'])
        distribution[rating] = row['count']

    # percentages for distribution bars
    distribution_pct = {i: (distribution[i] / total_reviews * 100) if total_reviews else 0 for i in range(1, 6)}

    # Track reviews the current session has marked as helpful (list of ints)
    voted = request.session.get('helpful_voted', [])

    context = {
        'reviews': reviews,
        'average_rating': round(float(average_rating), 1) if average_rating else 0.0,
        'average_int': int(round(float(average_rating))) if average_rating else 0,
        'review_count': total_reviews,
        'distribution': distribution,
        'distribution_pct': distribution_pct,
        'current_sort': sort,
        'current_rating': rating_filter,
        'total_helpful': total_helpful,
        'verified_count': verified_count,
    }

    # Build a lightweight list for template rendering with split dishes
    review_items = []
    for r in reviews:
        dishes = []
        if r.dishes_ordered:
            dishes = [d.strip() for d in r.dishes_ordered.split(',') if d.strip()]
        review_items.append({
            'id': r.review_id,
            'user_name': r.user_name,
            'rating': r.rating,
            'title': r.review_title,
            'text': r.review_text,
            'dishes': dishes,
            'date': r.submission_date,
            'helpful': getattr(r, 'helpful_count', 0),
            'would_recommend': r.would_you_recommend,
            'voted': (r.review_id in voted),
            'is_verified': r.is_verified,
        })

    context['review_items'] = review_items

    return render(request, 'review/review.html', context)


@require_POST
def review_helpful(request, pk):
    """Increment helpful_count for review with primary key `pk` and return JSON with new count.

    Expects a POST request. Returns JSON: {"helpful": <new_count>}.
    """
    try:
        review = Review.objects.get(pk=pk)
    except Review.DoesNotExist:
        return HttpResponseBadRequest('Invalid review id')

    # Prevent multiple helpful votes per session
    voted = request.session.get('helpful_voted', [])
    if pk in voted:
        # Already voted in this session; return current count and flag
        return JsonResponse({'helpful': review.helpful_count, 'already_voted': True})

    # Atomic increment
    Review.objects.filter(pk=pk).update(helpful_count=F('helpful_count') + 1)
    review.refresh_from_db()

    # Record in session
    try:
        # ensure we store ints
        voted.append(pk)
        request.session['helpful_voted'] = voted
    except Exception:
        # best-effort; don't block the response if session can't be updated
        pass

    return JsonResponse({'helpful': review.helpful_count, 'already_voted': False})


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
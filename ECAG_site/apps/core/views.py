from django.shortcuts import render
from django.db.models import Sum, Q, IntegerField
from django.db.models.functions import Coalesce
from apps.menu.models import MenuItem, Order, OrderItem
from apps.review.models import Review

def index(request): 
    popular_dishes = (
        MenuItem.objects.annotate(
            sold_qty=Coalesce(Sum('orderitem__quantity'), 0, output_field=IntegerField())
        )
        .order_by('-sold_qty', 'item_id')[:3]
    )

    latest_reviews = Review.objects.filter(is_verified=True).order_by('-submission_date')[:3]

    return render(request, 'core/index.html', {
        'featured_dishes': popular_dishes,
        'reviews': latest_reviews,
    })
def about(request):
    return render(request, "core/about.html")

def contact(request):
    return render(request, "core/contact.html")

from django.shortcuts import render
from django.db.models import Sum, Q, IntegerField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from apps.menu.models import MenuItem, Order, OrderItem
from apps.review.models import Review


def _featured_dishes_queryset():
    return (
        MenuItem.objects.annotate(
            sold_qty=Coalesce(Sum('orderitem__quantity'), 0, output_field=IntegerField())
        )
        .order_by('-sold_qty', 'item_id')[:3]
    )

def index(request): 
    popular_dishes = _featured_dishes_queryset()

    latest_reviews = Review.objects.filter(is_verified=True).order_by('-submission_date')[:3]

    return render(request, 'core/index.html', {
        'featured_dishes': popular_dishes,
        'reviews': latest_reviews,
    })


def mobile_featured_dishes(request):
    dishes = []
    for item in _featured_dishes_queryset():
        image_url = ""
        if item.menu_img:
            try:
                image_url = request.build_absolute_uri(item.menu_img.url)
            except Exception:
                image_url = ""

        dishes.append(
            {
                "item_id": item.item_id,
                "name": item.name,
                "desc": item.desc,
                "price": str(item.price),
                "image_url": image_url,
            }
        )

    return JsonResponse({"featured_dishes": dishes})


def about(request):
    return render(request, "core/about.html")

def contact(request):
    return render(request, "core/contact.html")

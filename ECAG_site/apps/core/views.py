from django.shortcuts import render
from django.db.models import Sum, Q, IntegerField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from apps.menu.models import MenuItem, Order, OrderItem
from apps.reservations.models import Reservation
from apps.review.models import Review
from django.utils import timezone
from django.utils.dateparse import parse_datetime


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


def mobile_notifications(request):
    since_raw = request.GET.get("since", "")
    since_dt = parse_datetime(since_raw) if since_raw else None
    if since_dt and timezone.is_naive(since_dt):
        since_dt = timezone.make_aware(since_dt, timezone.get_current_timezone())

    now = timezone.now()

    orders_qs = Order.objects.all().order_by("order_date")
    reservations_qs = Reservation.objects.all().order_by("created_at")

    if since_dt:
        orders_qs = orders_qs.filter(order_date__gt=since_dt)
        reservations_qs = reservations_qs.filter(created_at__gt=since_dt)
    else:
        orders_qs = orders_qs.order_by("-order_date")[:10]
        reservations_qs = reservations_qs.order_by("-created_at")[:10]

    events: list[dict] = []

    for order in orders_qs:
        label = order.order_id_str or f"ORD-{order.id:03d}"
        events.append(
            {
                "kind": "order",
                "event_id": f"order-{order.id}",
                "timestamp": order.order_date.isoformat(),
                "title": "Order Update",
                "message": f"Order {label} is {order.status.replace('_', ' ').title()}.",
            }
        )

    for booking in reservations_qs:
        events.append(
            {
                "kind": "reservation",
                "event_id": f"reservation-{booking.reservation_id}",
                "timestamp": booking.created_at.isoformat(),
                "title": "Reservation Update",
                "message": (
                    f"Reservation #{booking.reservation_id} for table {booking.table_id.table_number} "
                    f"is {booking.status.title()}."
                ),
            }
        )

    events.sort(key=lambda item: item["timestamp"])

    return JsonResponse({"server_time": now.isoformat(), "events": events})


def about(request):
    return render(request, "core/about.html")

def contact(request):
    return render(request, "core/contact.html")


def mobile_api_playground(request):
    return render(request, "core/mobile_api_playground.html")

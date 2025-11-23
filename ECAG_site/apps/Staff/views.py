from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
import datetime  # <--- Added import for custom date

from apps.menu.models import Order
from apps.reservations.models import Reservation, Table

# Helper function to get a staff user for development
def get_current_staff_user(request):
    # Returns request.user to bypass 404 errors during dev
    return request.user


# @login_required
# @user_passes_test(is_staff_user)
def staff_overview(request):
    staff_user = get_current_staff_user(request)
    # forcing date to Nov 17, 2025 for testing
    today = datetime.date(2025, 11, 17)
    # today = timezone.now().date() # <--- Commented out the real date

    todays_orders = Order.objects.filter(order_date__date=today)
    todays_orders_count = todays_orders.count()

    orders_in_progress_count = Order.objects.filter(status__in=['Preparing']).count()
    pending_orders_count = Order.objects.filter(status__in=['Pending']).count()

    todays_reservations = Reservation.objects.filter(date=today)
    todays_reservations_count = todays_reservations.count()
    upcoming_reservations_count = todays_reservations.filter(status='confirmed').count()
    pending_reservations_count = todays_reservations.filter(status='pending').count()

    active_orders = Order.objects.filter(status__in=['Pending', 'Preparing']).order_by('-order_date')[:5]
    reservations_today_list = todays_reservations.order_by('time')[:5]

    context = {
        'todays_orders_count': todays_orders_count,
        'orders_in_progress_count': orders_in_progress_count,
        'pending_orders_count': pending_orders_count,
        'todays_reservations_count': todays_reservations_count,
        'upcoming_reservations_count': upcoming_reservations_count,
        'pending_reservations_count': pending_reservations_count,
        'active_orders': active_orders,
        'reservations_today': reservations_today_list,
        'today_date': today,
        'active_page': 'staff_overview'
    }
    return render(request, 'staff/overview.html', context)

# @login_required
# @user_passes_test(is_staff_user)
def staff_orders(request):
    staff_user = get_current_staff_user(request)
    today = datetime.date(2025, 11, 17)
    # today = timezone.now().date()
    orders = Order.objects.filter(order_date__date=today).order_by('-order_date')
    context = {
        'orders': orders,
        'today_date': today,
        'active_page': 'staff_orders'
    }
    return render(request, 'staff/order.html', context)

# @login_required
# @user_passes_test(is_staff_user)
def staff_reservations(request):
    staff_user = get_current_staff_user(request)
    today = datetime.date(2025, 11, 17)
    # today = timezone.now().date()
    reservations = Reservation.objects.filter(date=today).order_by('time')

    total_reservations = reservations.count()
    pending_count = reservations.filter(status='pending').count()
    confirmed_count = reservations.filter(status='confirmed').count()
    seated_count = reservations.filter(status='seated').count()
    completed_count = reservations.filter(status='completed').count()
    cancelled_count = reservations.filter(status='cancelled').count()

    total_guests = reservations.aggregate(total=Sum('guest_count'))['total'] or 0


    context = {
        'reservations': reservations,
        'today_date': today,
        'total_reservations': total_reservations,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'seated_count': seated_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_guests': total_guests,
        'active_page': 'staff_reservations'
    }
    return render(request, 'staff/reservation.html', context)

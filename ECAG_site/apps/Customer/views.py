from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order, Reservation, Profile
from django.contrib.auth.models import User
from django.db.models import Sum, Q
import datetime

# Helper function to get the current user (real or fake)
def get_current_user(request):
    if request.user.is_authenticated:
        return request.user
    # Fallback to 'johndoe' for demonstration if no user is logged in
    return get_object_or_404(User, username='johndoe')

@login_required
def overview(request):
    customer = get_current_user(request)

    # Order statistics
    all_orders = Order.objects.filter(customer=customer)
    total_orders = all_orders.count()
    pending_orders = all_orders.filter(status__in=['Pending', 'Preparing']).count()
    total_spent = all_orders.filter(status='Completed').aggregate(total=Sum('orderitem__product__price', 'orderitem__quantity'))['total'] or 0.00

    # Reservation statistics
    all_reservations = Reservation.objects.filter(customer=customer)
    total_reservations = all_reservations.count()

    upcoming_reservations_count = all_reservations.filter(
        status='Confirmed',
        date__gte=datetime.date.today()
    ).count()

    recent_orders = all_orders[:3]
    recent_reservations = all_reservations[:3]

    context = {
        'user': customer,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_spent': f"{total_spent:.2f}",
        'total_reservations': total_reservations,
        'upcoming_reservations': upcoming_reservations_count,
        'recent_orders': recent_orders,
        'recent_reservations': recent_reservations,
    }
    # IMPORTANT: Note the namespaced template path
    return render(request, 'customer/overview.html', context)

@login_required
def my_orders(request):
    customer = get_current_user(request)
    orders = Order.objects.filter(customer=customer)
    context = {'orders': orders}
    # IMPORTANT: Note the namespaced template path
    return render(request, 'customer/my_orders.html', context)

@login_required
def my_reservations(request):
    customer = get_current_user(request)
    reservations = Reservation.objects.filter(customer=customer)
    context = {'reservations': reservations}
    # IMPORTANT: Note the namespaced template path
    return render(request, 'customer/my_reservations.html', context)

@login_required
def profile(request):
    customer = get_current_user(request)
    profile_data = customer.profile
    context = {
        'user': customer,
        'profile': profile_data,
    }
    # IMPORTANT: Note the namespaced template path
    return render(request, 'customer/profile.html', context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum

from apps.menu.models import Order
from apps.reservations.models import Reservation

# Helper function to get the current user
def get_current_user(request):
    if request.user.is_authenticated:
        return request.user

@login_required
def overview(request):
    customer = get_current_user(request)

    all_orders = Order.objects.filter(user=customer)
    total_orders = all_orders.count()
    pending_orders = all_orders.filter(status__in=['Pending']).count()
    preparing_orders = all_orders.filter(status__in=['Preparing']).count()

    #total_spent_data = all_orders.filter(status='Completed').aggregate(total=Sum('total'))
    #total_spent = total_spent_data['total'] or 0.00

    all_reservations = Reservation.objects.filter(user_id=customer)
    total_reservations = all_reservations.count()

    upcoming_reservations_count = all_reservations.filter(status='confirmed').count()

    recent_orders = all_orders.order_by('-order_date')[:3]
    recent_reservations = all_reservations.order_by('-date', '-time')[:3]

    context = {
        'user': customer,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        # 'total_spent': f"{total_spent:.2f}",
        'total_reservations': total_reservations,
        'upcoming_reservations': upcoming_reservations_count,
        'recent_orders': recent_orders,
        'recent_reservations': recent_reservations,
        'active_page': 'overview'
    }
    return render(request, 'customer/overview.html', context)

@login_required
def my_orders(request):
    customer = get_current_user(request)
    orders = Order.objects.filter(user=customer)
    context = {'orders': orders, 'active_page': 'my_orders'}
    return render(request, 'customer/my_orders.html', context)

@login_required
def my_reservations(request):
    customer = get_current_user(request)
    reservations = Reservation.objects.filter(user_id=customer).order_by('-date', '-time')
    context = {
        'reservations': reservations,
        'active_page': 'my_reservations'}
    return render(request, 'customer/my_reservations.html', context)

@login_required
def profile(request):
    customer = get_current_user(request)
    context = {
        'user': customer,
        'profile': customer.profile,
        'active_page': 'profile'
    }
    return render(request, 'customer/profile.html', context)

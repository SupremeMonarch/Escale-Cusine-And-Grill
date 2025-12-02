from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.contrib import messages
from .forms import UserUpdateForm

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

    active_deliveries_count = all_orders.filter(
        order_type__in=['Delivery', 'delivery'],
        delivery__delivery_status__in=['preparing_order', 'in_progress']
    ).count()

    all_reservations = Reservation.objects.filter(user_id=customer)
    total_reservations = all_reservations.count()

    upcoming_reservations_count = all_reservations.filter(status='confirmed').count()

    recent_orders = all_orders.order_by('-order_date')[:5] # Limit to 5 for overview
    recent_reservations = all_reservations.order_by('-date', '-time')[:5]

    context = {
        'user': customer,
        'total_orders': total_orders,
        'active_deliveries_count': active_deliveries_count, # New Stat
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
    orders = Order.objects.filter(user=customer).select_related('delivery').order_by('-order_date')
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
        'active_page': 'profile'
    }
    return render(request, 'customer/profile.html', context)

@login_required
def edit_profile(request):
    customer = get_current_user(request)

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=customer)

    context = {
        'form': form,
        'active_page': 'profile'
    }
    return render(request, 'customer/edit_profile.html', context)

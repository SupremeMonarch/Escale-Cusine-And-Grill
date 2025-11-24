from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import datetime

from apps.menu.models import Order
from apps.reservations.models import Reservation, Table

def is_staff_user(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff_user)
def staff_overview(request):
    today = timezone.now().date()

    todays_orders = Order.objects.filter(order_date__date=today)
    todays_orders_count = todays_orders.count()

    orders_in_progress_count = Order.objects.filter(status__in=['Preparing']).count()
    pending_orders_count = Order.objects.filter(status__in=['Pending']).count()

    active_reservations = Reservation.objects.filter(date__gte=today)
    active_reservations_count = active_reservations.count()
    upcoming_reservations_count = active_reservations.filter(status='confirmed').count()
    pending_reservations_count = active_reservations.filter(status='pending').count()

    active_orders = Order.objects.filter(status__in=['Pending', 'Preparing']).order_by('-order_date')[:5]
    reservations_active_list = active_reservations.order_by('time')[:5]

    context = {
        'todays_orders_count': todays_orders_count,
        'orders_in_progress_count': orders_in_progress_count,
        'pending_orders_count': pending_orders_count,
        'active_reservations_count': active_reservations_count,
        'upcoming_reservations_count': upcoming_reservations_count,
        'pending_reservations_count': pending_reservations_count,
        'active_orders': active_orders,
        'reservations_active': reservations_active_list,
        'today_date': today,
        'active_page': 'staff_overview'
    }
    return render(request, 'staff/overview.html', context)

@login_required
@user_passes_test(is_staff_user)
def staff_orders(request):
    today = timezone.now().date()
    orders = Order.objects.filter(order_date__date=today).order_by('-order_date')
    total_orders = orders.count()
    pending_orders = orders.filter(status__in=['Pending']).count()
    preparing_orders = orders.filter(status__in=['Preparing']).count()
    completed_orders = orders.filter(status__in=['Completed']).count()
    dine_in_orders = orders.filter(order_type__in=['Dine-in']).count()
    delivery_orders = orders.filter(order_type__in=['Delivery']).count()
    take_out_orders = orders.filter(order_type__in=['Take-out']).count()
    context = {
        'orders': orders,
        'today_date': today,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'completed_orders': completed_orders,
        'dine_in_orders': dine_in_orders,
        'delivery_orders': delivery_orders,
        'take_out_orders': take_out_orders,
        'active_page': 'staff_orders'
    }
    return render(request, 'staff/order.html', context)

@login_required
@user_passes_test(is_staff_user)
def staff_reservations(request):
    today = timezone.now().date()

    # Check if a specific date was requested via GET parameter
    selected_date_str = request.GET.get('date')
    selected_date = None

    if selected_date_str:
        try:
            # Parse the date string (YYYY-MM-DD)
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            # Filter exactly by this date
            reservations = Reservation.objects.filter(date=selected_date).order_by('time')
            view_title = f"Reservations for {selected_date.strftime('%b %d, %Y')}"
            view_subtitle = "Viewing specific date"
        except ValueError:
            # If date format is invalid, fallback to default
            reservations = Reservation.objects.filter(date__gte=today).order_by('date', 'time')
            view_title = "Upcoming Reservations"
            view_subtitle = f"Manage dining reservations from {today.strftime('%b %d, %Y')} onwards"
    else:
        # Default: Show today and future reservations
        reservations = Reservation.objects.filter(date__gte=today).order_by('date', 'time')
        view_title = "Upcoming Reservations"
        view_subtitle = f"Manage dining reservations from {today.strftime('%b %d, %Y')} onwards"

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
        'selected_date': selected_date_str, # Pass back string for input value
        'view_title': view_title,
        'view_subtitle': view_subtitle,
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

@require_POST
def update_order_status(request, order_id):
    try:
        data = json.loads(request.body)
        new_status = data.get('status')

        order = Order.objects.get(id=order_id)

        # Validate status if necessary
        if new_status in ['Pending', 'Preparing', 'Completed', 'Cancelled']:
            order.status = new_status
            order.save()
            return JsonResponse({'success': True, 'status': new_status})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status provided'}, status=400)

    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def update_reservation_status(request, reservation_id):
    try:
        data = json.loads(request.body)
        new_status = data.get('status') # e.g. 'confirmed', 'seated', 'completed', 'cancelled'

        new_status = new_status.lower()

        res = Reservation.objects.get(reservation_id=reservation_id)

        valid_statuses = ['pending', 'confirmed', 'seated', 'completed', 'cancelled']

        if new_status in valid_statuses:
            res.status = new_status
            res.save()
            return JsonResponse({'success': True, 'status': new_status})
        else:
             return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'}, status=400)

    except Reservation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Reservation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

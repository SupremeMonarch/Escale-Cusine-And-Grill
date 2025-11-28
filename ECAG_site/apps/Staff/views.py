from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import datetime

from apps.menu.models import Order, Delivery
from apps.reservations.models import Reservation, Table

def is_staff_user(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff_user)
def staff_overview(request):
    today = timezone.now().date()

    todays_orders = Order.objects.filter(order_date__date=today)
    todays_orders_count = todays_orders.count()

    active_deliveries_count = todays_orders.filter(
        order_type__in=['Delivery', 'delivery'],
        delivery__delivery_status__in=['preparing_order', 'in_progress']
    ).count()

    recent_orders = todays_orders.order_by('-order_date')

    todays_reservations_count = Reservation.objects.filter(date=today).count()
    active_reservations = Reservation.objects.filter(date__gte=today)
    active_reservations_count = active_reservations.count()
    upcoming_reservations_count = active_reservations.filter(status='confirmed').count()
    reservations_active_list = active_reservations.order_by('time')

    context = {
        'todays_orders_count': todays_orders_count,
        'active_deliveries_count': active_deliveries_count, # New Stat

        'active_reservations_count': active_reservations_count,
        'upcoming_reservations_count': upcoming_reservations_count,


        'active_orders': recent_orders,
        'reservations_active': reservations_active_list,
        'todays_reservations_count': todays_reservations_count,
        'today_date': today,
        'active_page': 'staff_overview'
    }
    return render(request, 'staff/overview.html', context)

@login_required
@user_passes_test(is_staff_user)
def staff_orders(request):
    today = timezone.now().date()
    orders = Order.objects.filter(order_date__date=today).select_related('delivery').order_by('-order_date')

    total_orders = orders.count()

    dine_in_orders = orders.filter(order_type__in=['Dine in', 'dine in']).count()
    delivery_orders = orders.filter(order_type__in=['Delivery', 'delivery']).count()
    take_out_orders = orders.filter(order_type__in=['pick up', 'Pick Up']).count()

    context = {
        'orders': orders,
        'today_date': today,
        'total_orders': total_orders,
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

    selected_date_str = request.GET.get('date')
    selected_date = None

    if selected_date_str:
        try:
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            reservations = Reservation.objects.filter(date=selected_date).order_by('time')
            view_title = f"Reservations for {selected_date.strftime('%b %d, %Y')}"
            view_subtitle = "Viewing specific date"
        except ValueError:
            reservations = Reservation.objects.filter(date__gte=today).order_by('date', 'time')
            view_title = "Upcoming Reservations"
            view_subtitle = f"Manage dining reservations from {today.strftime('%b %d, %Y')} onwards"
    else:
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
        'selected_date': selected_date_str,
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
    """
    Updates status ONLY for Delivery orders using the Delivery model status.
    """
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        order = Order.objects.get(id=order_id)

        # Check if it is a delivery order
        if order.order_type.lower() == 'delivery':
            if hasattr(order, 'delivery'):
                valid_statuses = [choice[0] for choice in Delivery.Status.choices]

                if new_status in valid_statuses:
                    order.delivery.delivery_status = new_status
                    order.delivery.save()
                    return JsonResponse({'success': True, 'status': new_status})
                else:
                    return JsonResponse({'success': False, 'error': f'Invalid delivery status. Allowed: {valid_statuses}'}, status=400)
            else:
                 return JsonResponse({'success': False, 'error': 'Delivery details missing for this order'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Status updates are only available for Delivery orders'}, status=400)

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

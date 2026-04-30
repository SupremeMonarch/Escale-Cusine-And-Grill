from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from apps.menu.models import Order, MenuItem, MenuSubCategory
from apps.reservations.models import Reservation
from django.db.models import Sum, Count, Avg, Q, Max
from apps.review.models import Review
from django.utils.timezone import now, timedelta
from decimal import Decimal, InvalidOperation
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
import secrets
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
from django.http import HttpResponse

User = get_user_model()  
logger = logging.getLogger(__name__)


def _save_menu_item_from_payload(item, *, name, desc, price, subcategory_id, is_available, image_file=None):
    name = (name or "").strip()
    desc = (desc or "").strip()

    if not name:
        raise ValueError("Item name is required")
    if not desc:
        raise ValueError("Description is required")

    try:
        price_value = Decimal(str(price or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Price must be a valid number")

    if price_value < 0:
        raise ValueError("Price cannot be negative")

    try:
        subcategory = MenuSubCategory.objects.get(id=subcategory_id)
    except (MenuSubCategory.DoesNotExist, TypeError, ValueError):
        raise ValueError("Choose a valid category")

    if isinstance(is_available, str):
        is_available = is_available.strip().lower() in {"1", "true", "yes", "on"}
    else:
        is_available = bool(is_available)

    item.name = name
    item.desc = desc
    item.price = price_value
    item.subcategory_id = subcategory
    item.is_available = is_available
    if not getattr(item, "pk", None) and not image_file:
        raise ValueError("Menu image is required")
    if image_file:
        item.menu_img = image_file
    item.save()
    return item

def overview(request):
    # --- TOTAL REVENUE ---
    total_revenue = Order.objects.filter(
        status=Order.Status.COMPLETED
    ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    # --- ACTIVE ORDERS ---
    active_orders = Order.objects.filter(
        status=Order.Status.IN_PROGRESS
    ).count()

    # --- PENDING RESERVATIONS ---
    pending_reservations = Reservation.objects.filter(
        status="pending"
    ).count()

    # --- TOTAL CUSTOMERS ---
    total_customers = User.objects.count()

    # --- RECENT ACTIVITIES ---
    recent_orders = Order.objects.select_related("user").order_by("-order_date")[:5]

    # --- POPULAR MENU ITEMS ---
    popular_qs = MenuItem.objects.annotate(
        order_count=Count("orderitem")
    ).order_by("-order_count")[:5]

    # compute revenue per item (price * order_count) and attach it
    popular_items = []
    for item in popular_qs:
        order_count = getattr(item, "order_count", 0) or 0
        price = item.price or Decimal("0.00")
        # attach revenue attribute for use in template
        item.revenue = (price * Decimal(order_count)).quantize(Decimal("0.01"))
        popular_items.append(item)

    # --- CHART DATA ---
    monthly_revenue = (
        Order.objects.filter(status=Order.Status.COMPLETED)
        .values("order_date__month")
        .annotate(total=Sum("total"))
        .order_by("order_date__month")
    )
    # Weekly revenue data
    today = now().date()
    week_start = today - timedelta(days=today.weekday())
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    
    chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    chart_data = []
    
    for date in week_dates:
        daily_revenue = Order.objects.filter(
            order_date__date=date
        ).aggregate(Sum('total'))['total__sum'] or 0
        chart_data.append(float(daily_revenue))
    
    context = {
        'total_revenue': total_revenue,
        'active_orders': active_orders,
        'pending_reservations': pending_reservations,
        'total_customers': total_customers,
        'popular_items': popular_items,
        'recent_orders': recent_orders,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    
    return render(request, 'admin_panel/overview.html', context)


STATUS_FLOW = {
    "pending": "confirmed",
    "confirmed": "preparing",
    "in_progress": "preparing",
    "preparing": "ready",
    "ready": "completed",
    "completed": None,
    "cancelled": None
}
def orders(request):
    qs = Order.objects.select_related("user").prefetch_related("items__item").order_by("-order_date")

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "all")
    type_filter = request.GET.get("type", "all")

    if search:
        if search.isdigit():
            qs = qs.filter(pk=search)
        else:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__phone__icontains=search)
            )

    if status_filter and status_filter != "all":
        qs = qs.filter(status=status_filter)

    if type_filter and type_filter != "all":
        qs = qs.filter(order_type__icontains=type_filter)

    context = {
        "orders": qs,
        "search_query": search,
        "status_filter": status_filter,
        "type_filter": type_filter,
    }
    return render(request, "admin_panel/orders.html", context)

def order_list(request):
    orders = Order.objects.all().select_related("user")

    # --- SEARCH ---
    search_query = request.GET.get("search", "").strip()
    if search_query:
        orders = orders.filter(order_id_str__icontains=search_query)

    # --- FILTER BY STATUS ---
    status_filter = request.GET.get("status")
    if status_filter and status_filter != "all":
        orders = orders.filter(status=status_filter)

    # --- FILTER BY ORDER TYPE ---
    type_filter = request.GET.get("type")
    if type_filter and type_filter != "all":
        orders = orders.filter(order_type=type_filter)

    context = {
        "orders": orders,
        "search_query": search_query,
        "status_filter": status_filter,
        "type_filter": type_filter,
    }
    return render(request, "admin_panel/orders.html", context)
def order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin_panel/order_detail.html', {'order': order})

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all() 

    return render(request, "admin_panel/order_detail.html", {
        "order": order,
        "items": items,
    })


@require_POST
def order_next_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

   
    next_status = STATUS_FLOW.get(order.status)
    if not next_status:
        
        messages.info(request, "Order is already in a final state.")
        return redirect(request.META.get("HTTP_REFERER", reverse("admin-orders")))

    order.status = next_status
    order.save(update_fields=["status"])
    messages.success(request, f"Order #{order.id} moved to {next_status}.")
    return redirect(request.META.get("HTTP_REFERER", reverse("admin-orders")))


@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status in ("completed", "cancelled"):
        messages.info(request, "Order cannot be cancelled.")
        return redirect(request.META.get("HTTP_REFERER", reverse("admin-orders")))

    order.status = "cancelled"
    order.save(update_fields=["status"])
    messages.success(request, f"Order #{order.id} cancelled.")
    
    return redirect(request.META.get("HTTP_REFERER", reverse("admin-orders")))

def reservations(request):
    # --- Search ---
    query = request.GET.get("q", "")

    # --- Status filter ---
    status = request.GET.get("status", "")

    reservations = Reservation.objects.select_related("user_id", "table_id")

    # Apply search
    if query:
        reservations = reservations.filter(
            Q(full_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(user_id__username__icontains=query)
        )

    # Apply status filter
    if status and status != "all":
        reservations = reservations.filter(status=status)

    # Default ordering from model: date then time
    reservations = reservations.order_by("date", "time")

    status_filters = {
        "all": "All",
        "pending": "Pending",
        "confirmed": "Confirmed",
        "seated": "Seated",
        "completed": "Completed",
        "cancelled": "Cancelled",
        "no-show": "No-Show",
    }

    context = {
        "reservations": reservations,
        "query": query,
        "current_status": status or "all",
        "status_filters": status_filters,
    }

    return render(request, "admin_panel/reservations.html", context)



@require_POST
def reservation_action(request, reservation_id):
    """
    Single POST endpoint for reservation actions:
      action = confirm | seat | complete | cancel
    """
    reservation = get_object_or_404(Reservation, reservation_id=reservation_id)
    action = request.POST.get("action", "").lower()

    allowed = {
        "confirm": "confirmed",
        "seat": "seated",
        "complete": "completed",
        "cancel": "cancelled",
    }

    new_status = allowed.get(action)
    if not new_status:
        messages.error(request, "Invalid action.")
        return redirect(request.META.get("HTTP_REFERER", reverse("admin-reservations")))

    # Prevent illegal transitions (optional)
    if reservation.status in ("completed", "cancelled"):
        messages.info(request, "This reservation is already finalized.")
        return redirect(request.META.get("HTTP_REFERER", reverse("admin-reservations")))

    reservation.status = new_status
    reservation.save(update_fields=["status"])
    messages.success(request, f"Reservation updated to {new_status}.")
    return redirect(request.META.get("HTTP_REFERER", reverse("admin-reservations")))





def menu(request):
    # --- Search query ---
    search_query = request.GET.get("search", "").strip()
    
    # --- Category filter ---
    category_id = request.GET.get("category", "")
    
    # Get all menu items
    menu_items = MenuItem.objects.select_related("subcategory_id").all()
    
    # Apply search filter
    if search_query:
        menu_items = menu_items.filter(
            Q(name__icontains=search_query) |
            Q(desc__icontains=search_query)
        )
    
    # Apply category filter
    if category_id:
        menu_items = menu_items.filter(subcategory_id_id=category_id)
    
    # Order by name
    menu_items = menu_items.order_by("name")
    
    # Get all categories for filter buttons
    categories = MenuSubCategory.objects.all().order_by("subcategory")
    
    # Handle POST requests for toggle actions
    if request.method == "POST":
        action = request.POST.get("action")
        item_id = request.POST.get("item_id")
        
        try:
            item = MenuItem.objects.get(item_id=item_id)
            
            if action == "toggle_availability":
                item.is_available = not item.is_available
                item.save()

            elif action == "create":
                try:
                    item = _save_menu_item_from_payload(
                        MenuItem(),
                        name=request.POST.get("name"),
                        desc=request.POST.get("desc"),
                        price=request.POST.get("price"),
                        subcategory_id=request.POST.get("subcategory_id"),
                        is_available=request.POST.get("is_available"),
                        image_file=request.FILES.get("menu_img"),
                    )
                    messages.success(request, f"{item.name} added to the menu.")
                except ValueError as exc:
                    messages.error(request, str(exc))

            elif action == "edit":
                try:
                    _save_menu_item_from_payload(
                        item,
                        name=request.POST.get("name"),
                        desc=request.POST.get("desc"),
                        price=request.POST.get("price"),
                        subcategory_id=request.POST.get("subcategory_id"),
                        is_available=request.POST.get("is_available"),
                        image_file=request.FILES.get("menu_img"),
                    )
                    messages.success(request, f"{item.name} updated.")
                except ValueError as exc:
                    messages.error(request, str(exc))

            elif action == "delete":
                item.delete()
        
        except MenuItem.DoesNotExist:
            pass
        
        # Redirect to same page to avoid form resubmission
        return redirect("admin-menu")
    
    context = {
        "menu_items": menu_items,
        "categories": categories,
        "search_query": search_query,
        "selected_category": category_id,
    }
    
    return render(request, "admin_panel/menu.html", context)


def customers(request):
    search_query = request.GET.get("search", "").strip()
    
    customers = User.objects.all()
    
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Annotate with order counts & totals per customer
    from django.db.models import Max
    
    customers = customers.annotate(
        orders_count=Count("order"),
        total_spent=Sum("order__total", filter=Q(order__status=Order.Status.COMPLETED)),
        last_order_date=Max("order__order_date", filter=Q(order__status=Order.Status.COMPLETED))
    ).order_by("-orders_count")
    
    # Add status based on annotation
    for c in customers:
        if c.orders_count >= 10:
            c.status = "VIP"
        elif c.orders_count > 0:
            c.status = "Active"
        else:
            c.status = "Regular"
    
    total_customers = User.objects.count()
    active_customers = User.objects.filter(order__isnull=False).distinct().count()
    vip_customers = customers.filter(orders_count__gte=10).count()
    total_revenue = Order.objects.filter(status=Order.Status.COMPLETED).aggregate(Sum("total"))["total__sum"] or Decimal("0.00")
    
    context = {
        "customers": customers,
        "search_query": search_query,
        "total_customers": total_customers,
        "active_customers": active_customers,
        "vip_customers": vip_customers,
        "total_revenue": f"Rs {total_revenue:,.2f}",
    }
    
    return render(request, "admin_panel/customers.html", context)


def staffs(request):
    search_query = request.GET.get("search", "").strip()
    
    # Get only users marked as staff (is_staff=True)
    staff_list = User.objects.filter(is_staff=True)
    
    if search_query:
        staff_list = staff_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    staff_list = staff_list.order_by("-date_joined")
    
    # Stats
    total_staff = User.objects.filter(is_staff=True).count()
    admin_count = User.objects.filter(is_staff=True, is_superuser=True).count()
    staff_count = User.objects.filter(is_staff=True, is_superuser=False).count()
    
    # Handle POST actions
    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        action = request.POST.get("action")
        
        try:
            staff = User.objects.get(id=staff_id, is_staff=True)
            
            if action == "make_admin" and not staff.is_superuser:
                staff.is_superuser = True
                staff.save()
                messages.success(request, f"{staff.first_name} is now an Admin.")
            
            elif action == "make_staff" and staff.is_superuser:
                staff.is_superuser = False
                staff.save()
                messages.success(request, f"{staff.first_name} is now a Staff Member.")
            
            elif action == "remove_access":
                staff.is_staff = False
                staff.is_superuser = False
                staff.save()
                messages.success(request, f"{staff.first_name}'s access has been removed.")
        
        except User.DoesNotExist:
            messages.error(request, "Staff member not found.")
        
        return redirect("admin-staffs")
    
    context = {
        "staff_list": staff_list,
        "search_query": search_query,
        "total_staff": total_staff,
        "admin_count": admin_count,
        "staff_count": staff_count,
    }
    
    return render(request, "admin_panel/staffs.html", context)

def invite_staff(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", "staff")
        
        # Validate email
        if not email:
            messages.error(request, "Email is required.")
            return redirect("admin-staffs")
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return redirect("admin-staffs")
        
        # Generate temporary password
        temp_password = secrets.token_urlsafe(12)
        
        try:
            # Create user with staff access
            user = User.objects.create_user(
                username=email.split('@')[0],
                email=email,
                password=temp_password,
                is_staff=True,
                is_superuser=(role == "admin")
            )
            
            # Send invitation email
            subject = "You've been invited to Escale Cuisine and Grill Staff"
            message = f"""Hello,

You've been invited to join the Escale Cuisine and Grill staff as a {role.capitalize()}.

Your login credentials:
Email: {email}
Temporary Password: {temp_password}

Please log in and change your password immediately for security.

Best regards,
Escale Cuisine and Grill Team"""
            
            send_mail(
                subject, 
                message, 
                "noreply@escalecuisine.com", 
                [email],
                fail_silently=False
            )
            messages.success(request, f"Staff member created and invitation sent to {email}")
            logger.info(f"Staff invited: {email} as {role}")
            
        except Exception as e:
            logger.error(f"Error inviting staff: {str(e)}")
            messages.error(request, f"Error: {str(e)}")
        
        return redirect("admin-staffs")
    
    return redirect("admin-staffs")

def reviews(request):
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "all")
    
    reviews_list = Review.objects.all()
    
    if search_query:
        reviews_list = reviews_list.filter(
            Q(review_title__icontains=search_query) |
            Q(review_text__icontains=search_query) |
            Q(user_name__icontains=search_query)
        )
    
    if status_filter == "pending":
        reviews_list = reviews_list.filter(is_verified=False)
    elif status_filter == "approved":
        reviews_list = reviews_list.filter(is_verified=True)
    
    reviews_list = reviews_list.order_by("-submission_date")
    
    total_reviews = Review.objects.count()
    avg_rating = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    pending_count = Review.objects.filter(is_verified=False).count()
    
    if request.method == "POST":
        action = request.POST.get("action")
        review_id = request.POST.get("review_id")
        
        try:
            review = Review.objects.get(review_id=review_id)
            
            if action == "verify":
                review.is_verified = True
                review.save()
                return JsonResponse({'success': True, 'message': 'Review verified.'})
            
            elif action == "email_response":
                subject = request.POST.get("subject")
                message = request.POST.get("message")
                recipient_email = review.email
                
                logger.info(f"Attempting to send email to {recipient_email}")
                logger.info(f"Subject: {subject}")
                
                try:
                    send_mail(
                        subject,
                        message,
                        "noreply@escalecuisine.com",
                        [recipient_email],
                        fail_silently=False
                    )
                    logger.info("Email sent successfully")
                    return JsonResponse({'success': True, 'message': 'Email sent successfully!'})
                except Exception as email_error:
                    logger.error(f"Email sending failed: {str(email_error)}")
                    return JsonResponse({'success': False, 'error': f'Email error: {str(email_error)}'})
            
            elif action == "delete":
                review.delete()
                return JsonResponse({'success': True, 'message': 'Review deleted.'})
        
        except Review.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Review not found.'})
        except Exception as e:
            logger.error(f"Error in reviews view: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    context = {
        "reviews": reviews_list,
        "search_query": search_query,
        "status_filter": status_filter,
        "total_reviews": total_reviews,
        "avg_rating": f"{avg_rating:.1f}",
        "pending_count": pending_count,
        "flagged_count": 0,
    }
    
    return render(request, "admin_panel/reviews.html", context)


def review_detail(request, review_id):
    review = get_object_or_404(Review, review_id=review_id)
    data = {
        'review_id': review.review_id,
        'user_name': review.user_name,
        'email': review.email,
        'rating': review.rating,
        'review_title': review.review_title,
        'review_text': review.review_text,
        'submission_date': review.submission_date.isoformat(),
        'is_verified': review.is_verified,
        'dishes_ordered': review.dishes_ordered or '',
        'would_recommend': review.would_you_recommend or 'neutral',
        'helpful_votes': review.helpful_count or 0,
    }
    return JsonResponse(data)


def _json_error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _unique_username_from_email(email: str) -> str:
    base = (email.split('@')[0] or 'staff').strip()[:120]
    candidate = base
    i = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}{i}"
        i += 1
    return candidate


@csrf_exempt
def mobile_overview_data(request):
    if request.method != 'GET':
        return _json_error('GET required', 405)

    total_revenue = Order.objects.filter(status=Order.Status.COMPLETED).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    active_orders = Order.objects.filter(status=Order.Status.IN_PROGRESS).count()
    pending_reservations = Reservation.objects.filter(status='pending').count()
    total_customers = User.objects.count()

    recent_orders = list(
        Order.objects.select_related('user')
        .order_by('-order_date')[:10]
        .values('id', 'order_id_str', 'status', 'order_type', 'total', 'order_date')
    )

    # --- Weekly daily revenue (last 7 days) ---
    today = now().date()
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_revenue = Order.objects.filter(
            status=Order.Status.COMPLETED,
            order_date__date=day,
        ).aggregate(total=Sum('total'))['total'] or 0
        chart_labels.append(day.strftime('%a'))
        chart_data.append(float(day_revenue))

    return JsonResponse({
        'ok': True,
        'metrics': {
            'total_revenue': str(total_revenue),
            'active_orders': active_orders,
            'pending_reservations': pending_reservations,
            'total_customers': total_customers,
        },
        'recent_orders': recent_orders,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })


@csrf_exempt
def mobile_orders_data(request):
    if request.method != 'GET':
        return _json_error('GET required', 405)

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')

    qs = Order.objects.select_related('user').prefetch_related('items__item').order_by('-order_date')

    if search:
        if search.isdigit():
            qs = qs.filter(pk=search)
        else:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(order_id_str__icontains=search)
            )

    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    if type_filter and type_filter != 'all':
        qs = qs.filter(order_type__icontains=type_filter)

    orders_payload = []
    for o in qs[:300]:
        items_payload = []
        for it in o.items.all()[:8]:
            items_payload.append({
                'name': getattr(it.item, 'name', 'Item'),
                'quantity': it.quantity,
                'price': str(getattr(it.item, 'price', '0.00') or '0.00'),
                'subtotal': str(it.subtotal),
            })

        delivery_info = None
        try:
            d = o.delivery
            delivery_info = {
                'address': d.address,
                'fee': str(d.fee),
                'delivery_status': d.delivery_status,
                'arrival_time': str(d.arrival_time) if d.arrival_time else None,
            }
        except Exception:
            pass

        orders_payload.append({
            'id': o.id,
            'order_id_str': o.order_id_str,
            'status': o.status,
            'order_type': o.order_type,
            'subtotal': str(o.subtotal),
            'total': str(o.total),
            'order_date': o.order_date.isoformat() if o.order_date else None,
            'user': {
                'id': o.user_id,
                'name': (o.user.get_full_name() if o.user else '') or (o.user.username if o.user else 'Guest'),
                'email': o.user.email if o.user else '',
                'phone': getattr(o.user, 'phone', '') or '',
            },
            'items': items_payload,
            'delivery': delivery_info,
        })

    return JsonResponse({'ok': True, 'orders': orders_payload})


@csrf_exempt
def mobile_order_action(request, order_id):
    if request.method != 'POST':
        return _json_error('POST required', 405)

    order = get_object_or_404(Order, id=order_id)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    action = (payload.get('action') or '').lower()
    status = (payload.get('status') or '').lower()

    if action == 'next':
        next_status = STATUS_FLOW.get(order.status)
        if not next_status:
            return _json_error('Order is already in a final state', 400)
        order.status = next_status
    elif action == 'cancel':
        if order.status in ('completed', 'cancelled'):
            return _json_error('Order cannot be cancelled', 400)
        order.status = 'cancelled'
    elif status:
        order.status = status
    else:
        return _json_error('Action or status is required', 400)

    order.save(update_fields=['status'])
    return JsonResponse({'ok': True, 'status': order.status})


@csrf_exempt
def mobile_reservations_data(request):
    if request.method != 'GET':
        return _json_error('GET required', 405)

    query = request.GET.get('q', '')
    status = request.GET.get('status', 'all')

    reservations_qs = Reservation.objects.select_related('user_id', 'table_id')

    if query:
        reservations_qs = reservations_qs.filter(
            Q(full_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(user_id__username__icontains=query)
        )

    if status and status != 'all':
        reservations_qs = reservations_qs.filter(status=status)

    reservations_qs = reservations_qs.order_by('date', 'time')[:300]

    payload = []
    for r in reservations_qs:
        payload.append({
            'reservation_id': r.reservation_id,
            'status': r.status,
            'date': r.date.isoformat() if r.date else None,
            'time': r.time.isoformat() if r.time else None,
            'guest_count': r.guest_count,
            'full_name': r.full_name,
            'phone': r.phone,
            'email': r.email,
            'table': {
                'table_id': r.table_id_id,
                'table_number': r.table_id.table_number if r.table_id else None,
            },
            'user': {
                'id': r.user_id_id,
                'username': r.user_id.username if r.user_id else '',
            },
        })

    return JsonResponse({'ok': True, 'reservations': payload})


@csrf_exempt
def mobile_reservation_action(request, reservation_id):
    if request.method != 'POST':
        return _json_error('POST required', 405)

    reservation = get_object_or_404(Reservation, reservation_id=reservation_id)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    action = (payload.get('action') or '').lower()
    new_status = (payload.get('status') or '').lower()

    allowed = {
        'confirm': 'confirmed',
        'seat': 'seated',
        'complete': 'completed',
        'cancel': 'cancelled',
    }

    if not new_status:
        new_status = allowed.get(action)

    if not new_status:
        return _json_error('Invalid action/status', 400)

    if reservation.status in ('completed', 'cancelled') and new_status not in ('completed', 'cancelled'):
        return _json_error('Reservation is already finalized', 400)

    reservation.status = new_status
    reservation.save(update_fields=['status'])
    return JsonResponse({'ok': True, 'status': reservation.status})


@csrf_exempt
def mobile_menu_data(request):
    if request.method == 'GET':
        search_query = request.GET.get('search', '').strip()
        category_id = request.GET.get('category', '')

        menu_items = MenuItem.objects.select_related('subcategory_id').all()
        if search_query:
            menu_items = menu_items.filter(Q(name__icontains=search_query) | Q(desc__icontains=search_query))
        if category_id and category_id != 'all':
            menu_items = menu_items.filter(subcategory_id_id=category_id)

        payload = []
        for item in menu_items.order_by('name')[:500]:
            if item.menu_img:
                image_url = request.build_absolute_uri(item.menu_img.url)
            else:
                image_url = ''
            payload.append({
                'item_id': item.item_id,
                'name': item.name,
                'desc': item.desc,
                'price': str(item.price),
                'is_available': item.is_available,
                'subcategory_id': item.subcategory_id_id,
                'subcategory': item.subcategory_id.subcategory if item.subcategory_id else '',
                'image_url': image_url,
            })

        categories = [
            {'subcategory_id': c.id, 'subcategory': c.subcategory}
            for c in MenuSubCategory.objects.order_by('subcategory')
        ]
        return JsonResponse({'ok': True, 'menu_items': payload, 'categories': categories})

    if request.method == 'POST':
        if (request.content_type or '').startswith('application/json'):
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
            image_file = None
        else:
            payload = request.POST
            image_file = request.FILES.get('menu_img')

        action = payload.get('action')

        if action == 'create':
            try:
                item = _save_menu_item_from_payload(
                    MenuItem(),
                    name=payload.get('name'),
                    desc=payload.get('desc'),
                    price=payload.get('price'),
                    subcategory_id=payload.get('subcategory_id'),
                    is_available=payload.get('is_available'),
                    image_file=image_file,
                )
            except ValueError as exc:
                return _json_error(str(exc), 400)
            return JsonResponse({'ok': True, 'item_id': item.item_id})

        item_id = payload.get('item_id')
        item = get_object_or_404(MenuItem, item_id=item_id)

        if action == 'toggle_availability':
            item.is_available = not item.is_available
            item.save(update_fields=['is_available'])
            return JsonResponse({'ok': True, 'is_available': item.is_available})
        if action == 'edit':
            try:
                _save_menu_item_from_payload(
                    item,
                    name=payload.get('name'),
                    desc=payload.get('desc'),
                    price=payload.get('price'),
                    subcategory_id=payload.get('subcategory_id'),
                    is_available=payload.get('is_available'),
                    image_file=image_file,
                )
            except ValueError as exc:
                return _json_error(str(exc), 400)
            return JsonResponse({'ok': True})
        if action == 'delete':
            item.delete()
            return JsonResponse({'ok': True})

        return _json_error('Invalid action', 400)

    return _json_error('Unsupported method', 405)


@csrf_exempt
def mobile_customers_data(request):
    if request.method != 'GET':
        return _json_error('GET required', 405)

    search_query = request.GET.get('search', '').strip()
    customers_qs = User.objects.all()

    if search_query:
        customers_qs = customers_qs.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(username__icontains=search_query)
        )

    customers_qs = customers_qs.annotate(
        orders_count=Count('order'),
        total_spent=Sum('order__total', filter=Q(order__status=Order.Status.COMPLETED)),
        last_order_date=Max('order__order_date', filter=Q(order__status=Order.Status.COMPLETED)),
    ).order_by('-orders_count')

    customers = []
    for c in customers_qs[:500]:
        if c.orders_count >= 10:
            status = 'VIP'
        elif c.orders_count > 0:
            status = 'Regular'
        else:
            status = 'New'

        customers.append({
            'id': c.id,
            'name': c.get_full_name() or c.username,
            'email': c.email,
            'orders_count': c.orders_count or 0,
            'total_spent': str(c.total_spent or Decimal('0.00')),
            'status': status,
            'last_order_date': c.last_order_date.isoformat() if c.last_order_date else None,
        })

    total_customers = User.objects.count()
    active_customers = User.objects.filter(order__isnull=False).distinct().count()
    vip_customers = sum(1 for c in customers if str(c['status']).lower() == 'vip')

    return JsonResponse(
        {
            'ok': True,
            'stats': {
                'total_customers': total_customers,
                'active_customers': active_customers,
                'vip_customers': vip_customers,
            },
            'customers': customers,
        }
    )


@csrf_exempt
def mobile_staffs_data(request):
    if request.method == 'GET':
        search_query = request.GET.get('search', '').strip()
        staff_qs = User.objects.filter(is_staff=True)

        if search_query:
            staff_qs = staff_qs.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(username__icontains=search_query)
            )

        payload = []
        for s in staff_qs.order_by('-date_joined')[:500]:
            payload.append(
                {
                    'id': s.id,
                    'name': s.get_full_name() or s.username,
                    'email': s.email,
                    'is_admin': bool(s.is_superuser),
                    'date_joined': s.date_joined.isoformat() if s.date_joined else None,
                }
            )

        return JsonResponse(
            {
                'ok': True,
                'stats': {
                    'total_staff': User.objects.filter(is_staff=True).count(),
                    'admin_count': User.objects.filter(is_staff=True, is_superuser=True).count(),
                    'staff_count': User.objects.filter(is_staff=True, is_superuser=False).count(),
                },
                'staff_list': payload,
            }
        )

    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}

        action = payload.get('action')
        staff_id = payload.get('staff_id')

        staff = get_object_or_404(User, id=staff_id, is_staff=True)

        if action == 'make_admin' and not staff.is_superuser:
            staff.is_superuser = True
            staff.save(update_fields=['is_superuser'])
        elif action == 'make_staff' and staff.is_superuser:
            staff.is_superuser = False
            staff.save(update_fields=['is_superuser'])
        elif action == 'remove_access':
            staff.is_staff = False
            staff.is_superuser = False
            staff.save(update_fields=['is_staff', 'is_superuser'])
        else:
            return _json_error('Invalid action', 400)

        return JsonResponse({'ok': True})

    return _json_error('Unsupported method', 405)


@csrf_exempt
def mobile_invite_staff(request):
    if request.method != 'POST':
        return _json_error('POST required', 405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    email = (payload.get('email') or '').strip()
    role = payload.get('role', 'staff')

    if not email:
        return _json_error('Email is required', 400)

    if User.objects.filter(email=email).exists():
        return _json_error('This email is already registered', 400)

    temp_password = secrets.token_urlsafe(12)

    try:
        User.objects.create_user(
            username=_unique_username_from_email(email),
            email=email,
            password=temp_password,
            is_staff=True,
            is_superuser=(role == 'admin'),
        )

        subject = "You've been invited to Escale Cuisine and Grill Staff"
        message = f"""Hello,\n\nYou've been invited to join Escale staff as {role.capitalize()}.\n\nEmail: {email}\nTemporary Password: {temp_password}\n\nPlease log in and change your password immediately.\n"""
        send_mail(subject, message, 'noreply@escalecuisine.com', [email], fail_silently=False)

    except Exception as exc:
        return _json_error(str(exc), 500)

    return JsonResponse({'ok': True})


@csrf_exempt
def mobile_reviews_data(request):
    if request.method != 'GET':
        return _json_error('GET required', 405)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')

    reviews_qs = Review.objects.all()

    if search_query:
        reviews_qs = reviews_qs.filter(
            Q(review_title__icontains=search_query)
            | Q(review_text__icontains=search_query)
            | Q(user_name__icontains=search_query)
        )

    if status_filter == 'pending':
        reviews_qs = reviews_qs.filter(is_verified=False)
    elif status_filter == 'approved':
        reviews_qs = reviews_qs.filter(is_verified=True)

    payload = []
    for review in reviews_qs.order_by('-submission_date')[:500]:
        payload.append(
            {
                'review_id': review.review_id,
                'user_name': review.user_name,
                'email': review.email,
                'rating': review.rating,
                'review_title': review.review_title,
                'review_text': review.review_text,
                'submission_date': review.submission_date.isoformat() if review.submission_date else None,
                'is_verified': review.is_verified,
            }
        )

    total_reviews = Review.objects.count()
    avg_rating = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    pending_count = Review.objects.filter(is_verified=False).count()

    return JsonResponse(
        {
            'ok': True,
            'stats': {
                'total_reviews': total_reviews,
                'avg_rating': float(avg_rating),
                'pending_count': pending_count,
            },
            'reviews': payload,
        }
    )


@csrf_exempt
def mobile_review_action(request, review_id):
    if request.method != 'POST':
        return _json_error('POST required', 405)

    review = get_object_or_404(Review, review_id=review_id)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    action = payload.get('action')

    if action == 'verify':
        review.is_verified = True
        review.save(update_fields=['is_verified'])
        return JsonResponse({'ok': True})

    if action == 'delete':
        review.delete()
        return JsonResponse({'ok': True})

    if action == 'email_response':
        subject = payload.get('subject') or 'Response to your review'
        message = payload.get('message') or ''
        send_mail(subject, message, 'noreply@escalecuisine.com', [review.email], fail_silently=False)
        return JsonResponse({'ok': True})

    return _json_error('Invalid action', 400)

def export_orders(request):
    orders = Order.objects.select_related('user').all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Total', 'Status', 'Date'])
    
    for order in orders:
        writer.writerow([
            order.id,
            order.user.get_full_name() or order.user.username,
            order.user.email,
            f"Rs {order.total}",
            order.status or 'Pending',
            order.order_date.strftime('%Y-%m-%d %H:%M'),
        ])
    
    return response

def export_reservations(request):
    reservations = Reservation.objects.select_related('user').all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reservations.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Reservation ID', 'Customer', 'Email', 'Phone', 'Guests', 'Date', 'Time', 'Status'])
    
    for res in reservations:
        writer.writerow([
            res.id,
            res.user.get_full_name() or res.user.username,
            res.user.email,
            res.phone or 'N/A',
            res.number_of_guests,
            res.reservation_date.strftime('%Y-%m-%d'),
            res.reservation_time.strftime('%H:%M'),
            res.status or 'Pending',
        ])
    
    return response

def export_reviews(request):
    reviews = Review.objects.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reviews.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Review ID', 'Customer', 'Email', 'Rating', 'Title', 'Review Text', 'Verified', 'Date'])
    
    for review in reviews:
        writer.writerow([
            review.review_id,
            review.user_name,
            review.email,
            review.rating,
            review.review_title,
            review.review_text,
            'Yes' if review.is_verified else 'No',
            review.submission_date.strftime('%Y-%m-%d %H:%M'),
        ])
    
    return response
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from apps.menu.models import Order, MenuItem, MenuSubCategory
from apps.reservations.models import Reservation
from django.db.models import Sum, Count, Avg, Q
from apps.review.models import Review
from django.utils.timezone import now, timedelta
from decimal import Decimal
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
    "preparing": "ready",
    "ready": "completed",
    "completed": None,
    "cancelled": None
}
def orders(request):
    qs = Order.objects.select_related("user").order_by("-order_date")

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
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from decimal import Decimal
from .models import MenuCategory, MenuItem, Order, OrderItem, Transaction, TOPPING_PRICES, eligible_for_toppings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Flat delivery fee to mirror frontend snapshot
DELIVERY_FEE = Decimal("100.00")
TAKEOUT_FEE = Decimal("50.00")
def _reset_cart_session(session):
    """Utility to fully clear cart/session order artifacts so sidebar resets."""
    for key in ["cart_items", "cart_order_id", "order"]:
        session.pop(key, None)
    # Leave last_order_id so success page can still render once.
    session.modified = True


def _build_sections(category_name):
    category = get_object_or_404(MenuCategory, category=category_name)
    sections = {}
    for sub in category.menusubcategory_set.all():
        items = sub.menuitem_set.filter(is_available=True)
        if items.exists():
            sections[sub.subcategory.upper()] = items
    return sections


def menu_starters(request):
    sections = _build_sections("Starters")
    return render(request, "menu_starters.html", {"sections": sections, "active": "starters"})


def menu_main_course(request):
    sections = _build_sections("Main Course")
    return render(request, "menu_main_course.html", {"sections": sections, "active": "main_course"})


def menu_beverages(request):
    sections = _build_sections("Beverages")
    return render(request, "menu_beverages.html", {"sections": sections, "active": "beverages"})


def checkout(request):
    """GET: Display checkout page with order preview from session.
       POST: Complete the order and transaction, mark as COMPLETED."""
    if request.method == "POST":
        # Retrieve the in-progress order from session
        order_id = request.session.get('checkout_order_id')
        if not order_id:
            # No order found, redirect back to checkout
            return redirect("menu:checkout")
        
        try:
            order = Order.objects.get(pk=order_id, status=Order.Status.IN_PROGRESS)
        except Order.DoesNotExist:
            return redirect("menu:checkout")

        raw_method = request.POST.get("payment_method") or "card"
        if raw_method == "card":
            pm = Transaction.Method.CREDIT_CARD
        elif raw_method == "paypal":
            pm = Transaction.Method.PAYPAL
        elif raw_method == "juice":
            pm = Transaction.Method.JUICE
        else:
            pm = Transaction.Method.MYT_MOB

        try:
            with db_transaction.atomic():
                # Update transaction with payment details and mark complete
                try:
                    txn = Transaction.objects.get(order=order, status=Transaction.Status.IN_PROGRESS)
                except Transaction.DoesNotExist:
                    # Create transaction if it doesn't exist
                    txn = Transaction(order=order, payment_method=pm, status=Transaction.Status.IN_PROGRESS)
                
                txn.payment_method = pm
                # Capture card fields only if credit card chosen
                if pm == Transaction.Method.CREDIT_CARD:
                    txn.card_name = request.POST.get("card_name", "")
                    txn.card_number = request.POST.get("card_number", "")
                    raw_exp = request.POST.get("exp_date")
                    if raw_exp:
                        from datetime import datetime
                        try:
                            txn.exp_date = datetime.strptime(raw_exp, "%Y-%m-%d").date()
                        except Exception:
                            pass
                    txn.cvv = request.POST.get("cvv", "")
                else:
                    txn.card_name = ""
                    txn.card_number = ""
                    txn.exp_date = None
                    txn.cvv = ""
                
                txn.status = Transaction.Status.COMPLETED
                txn.save()
                
                # Mark order as completed
                order.status = Order.Status.COMPLETED
                order.save()
                
                # Clear cart-related session state
                _reset_cart_session(request.session)
                request.session["cart_items"] = []
                request.session.pop('checkout_order_id', None)
                request.session.modified = True
                request.session["last_order_id"] = order.id
        except Exception as e:
            # Log error but still redirect
            print(f"Error completing order: {e}")
            pass
        
        return redirect("menu:checkout_success")

    # GET: Create order from session cart if not already created
    order_id = request.session.get('checkout_order_id')
    order = None
    
    if order_id:
        try:
            order = Order.objects.get(pk=order_id, status=Order.Status.IN_PROGRESS)
        except Order.DoesNotExist:
            order = None
    
    # If no order exists, we'll show preview from session (create on first visit)
    sess_cart = request.session.get("cart_items", [])
    
    if not sess_cart:
        # Empty cart, redirect to menu
        return redirect("menu:menu_starters")
    
    item_ids = [int(x.get('item_id')) for x in sess_cart if x.get('item_id')]
    items_map = {m.item_id: m for m in MenuItem.objects.filter(item_id__in=item_ids)} if item_ids else {}

    rebuilt = []
    subtotal_sum = Decimal("0.00")
    items_count = 0
    for x in sess_cart:
        iid = int(x.get('item_id')) if x.get('item_id') else None
        qty = int(x.get('quantity', 1) or 1)
        items_count += qty
        mi = items_map.get(iid)
        if not mi:
            continue
        # per-unit price = base + toppings
        unit_price = Decimal(mi.price)
        if eligible_for_toppings(getattr(mi, 'name', '')):
            meat = x.get('meat_topping') or ''
            if meat:
                unit_price += TOPPING_PRICES.get(meat, Decimal('0.00'))
            extras = x.get('extra_toppings') or []
            for t in extras:
                if t:
                    unit_price += TOPPING_PRICES.get(t, Decimal('0.00'))
        line_sub = unit_price * qty
        subtotal_sum += line_sub
        image_url = None
        if getattr(mi, "menu_img", None):
            try:
                image_url = mi.menu_img.url
            except Exception:
                image_url = None
        toppings_list = []
        if x.get('meat_topping'):
            toppings_list.append(x['meat_topping'])
        if x.get('extra_toppings'):
            for t in x['extra_toppings']:
                if t:
                    toppings_list.append(t)
        rebuilt.append({
            "item_id": mi.item_id,
            "name": mi.name,
            "price": unit_price,
            "quantity": qty,
            "subtotal": line_sub,
            "image_url": image_url,
            "toppings": toppings_list,
        })

    raw_type = request.session.get('order_type_raw')
    delivery_fee = DELIVERY_FEE if raw_type == 'delivery' else (TAKEOUT_FEE if raw_type == 'pick_up' else Decimal("0.00"))
    fee_label = 'Delivery' if raw_type == 'delivery' else ('Take Out' if raw_type == 'pick_up' else 'Dine In')
    type_label = 'Delivery' if raw_type == 'delivery' else ('Pick Up' if raw_type == 'pick_up' else 'Dine In')
    
    # If this is the first GET request, create the order now with IN_PROGRESS status
    if not order:
        ORDER_TYPE_MAP = {
            'dine_in': Order.Ordertype.DINE_IN,
            'pick_up': Order.Ordertype.CARRY_OUT,
            'delivery': Order.Ordertype.DELIVERY,
        }
        mapped_ot = ORDER_TYPE_MAP.get(raw_type) or Order.Ordertype.DELIVERY
        
        try:
            with db_transaction.atomic():
                # Create order with IN_PROGRESS status
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    order_type=mapped_ot,
                    status=Order.Status.IN_PROGRESS,
                )
                
                # Create OrderItems from session cart
                for x in sess_cart:
                    iid = x.get('item_id')
                    qty = int(x.get('quantity', 1) or 1)
                    meat = x.get('meat_topping') or ''
                    extras = x.get('extra_toppings') or []
                    if not iid:
                        continue
                    try:
                        menu_item = MenuItem.objects.get(pk=int(iid))
                    except MenuItem.DoesNotExist:
                        continue
                    OrderItem.objects.create(
                        order=order,
                        item=menu_item,
                        quantity=qty,
                        meat_topping=meat,
                        extra_toppings=",".join([e for e in extras if e]),
                    )
                
                # Create Delivery/Takeout record
                if mapped_ot == Order.Ordertype.DELIVERY:
                    from .models import Delivery
                    Delivery.objects.create(order=order, address="TBD", fee=DELIVERY_FEE)
                elif mapped_ot == Order.Ordertype.CARRY_OUT:
                    from .models import Takeout
                    Takeout.objects.create(order=order, fee=TAKEOUT_FEE)
                
                # Update totals
                order.update_total()
                
                # Create transaction with IN_PROGRESS status
                Transaction.objects.create(
                    order=order,
                    payment_method=Transaction.Method.CREDIT_CARD,
                    status=Transaction.Status.IN_PROGRESS,
                )
                
                # Store order ID in session
                request.session['checkout_order_id'] = order.id
                request.session.modified = True
        except Exception as e:
            print(f"Error creating order: {e}")
            # If order creation fails, show preview from session
            pass
    
    order_ctx = {
        "order_type": raw_type or "delivery",
        "get_order_type_display": None,
        "order_type_display": type_label,
        "items_count": items_count,
        "delivery": delivery_fee,
        "fee_label": fee_label,
        "subtotal": subtotal_sum,
        "total": subtotal_sum + delivery_fee,
    }
    return render(
        request,
        "checkout.html",
        {
            "cart_items": rebuilt,
            "order": order_ctx,
            "form_errors": {},
            "payment_method": None,
            "card_name": "",
            "card_number": "",
            "exp_date": "",
            "cvv": "",
        },
    )


@csrf_exempt
def save_cart(request):
    """Accept JSON payload { items: [{item_id, quantity}, ...] } and store
    a normalized `cart_items` list in the session for checkout processing.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    items = payload.get('items') or []
    raw_order_type = payload.get('order_type')  # expect values: dine_in, pick_up, delivery
    normalized = []
    for it in items:
        try:
            iid = int(it.get('item_id')) if it.get('item_id') is not None else None
        except Exception:
            iid = None
        qty = int(it.get('quantity', 1) or 1)
        meat = it.get('meat_topping') or ''
        extras = it.get('extra_toppings') or []
        if iid is None:
            continue
        normalized.append({
            'item_id': iid,
            'quantity': qty,
            'meat_topping': meat,
            'extra_toppings': extras,
        })

    request.session['cart_items'] = normalized
    request.session.modified = True

    # Map frontend order type (dine_in | pick_up | delivery) to model choices ("dine in" | "carry out" | "delivery")
    ORDER_TYPE_MAP = {
        'dine_in': Order.Ordertype.DINE_IN,
        'pick_up': Order.Ordertype.CARRY_OUT,
        'delivery': Order.Ordertype.DELIVERY,
    }
    mapped = ORDER_TYPE_MAP.get(raw_order_type)
    if raw_order_type:
        request.session['order_type_raw'] = raw_order_type
        request.session.modified = True

    return JsonResponse({'ok': True, 'count': len(normalized)})


def checkout_success(request):
    last_id = request.session.get('last_order_id')
    order = None
    txn = None
    if last_id:
        try:
            # prefetch related items for efficiency
            order = Order.objects.prefetch_related('items__item', 'transactions').get(pk=last_id)
            txn = order.transactions.order_by('-id').first()
        except Order.DoesNotExist:
            order = None
    # Ensure sidebar/cart cleared post-success even if direct navigation occurred.
    _reset_cart_session(request.session)
    return render(request, 'checkout_success.html', {'order': order, 'transaction': txn})

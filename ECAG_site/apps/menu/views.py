from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from decimal import Decimal
from .models import MenuCategory, MenuItem, Order, OrderItem, Transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
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
    """Unconditional checkout: any payment method succeeds and redirects."""
    if request.method == "POST":
        raw_method = request.POST.get("payment_method") or "card"
        if raw_method == "card":
            pm = Transaction.Method.CREDIT_CARD
        elif raw_method == "paypal":
            pm = Transaction.Method.PAYPAL
        elif raw_method == "juice":
            pm = Transaction.Method.JUICE
        else:
            pm = Transaction.Method.MYT_MOB
        cart_items = request.session.get("cart_items", [])
        try:
            with db_transaction.atomic():
                order = None
                cart_order_id = request.session.get("cart_order_id")
                if cart_order_id:
                    try:
                        order = Order.objects.get(pk=cart_order_id)
                    except Order.DoesNotExist:
                        order = None
                if not order:
                    order = Order.get_or_create_cart(
                        request.user if request.user.is_authenticated else None,
                        request.session,
                    )
                if cart_items:
                    order.sync_items_from_cart(cart_items)
                # Apply order type from session if present (user may have changed it client-side)
                raw_type = request.session.get('order_type_raw')
                if raw_type:
                    ORDER_TYPE_MAP = {
                        'dine_in': Order.Ordertype.DINE_IN,
                        'pick_up': Order.Ordertype.CARRY_OUT,
                        'delivery': Order.Ordertype.DELIVERY,
                    }
                    mapped_ot = ORDER_TYPE_MAP.get(raw_type)
                    if mapped_ot and mapped_ot != order.order_type:
                        order.order_type = mapped_ot
                        order.save(update_fields=['order_type'])
                # Apply order type from session if present (user may have changed it client-side)
                raw_type = request.session.get('order_type_raw')
                if raw_type:
                    ORDER_TYPE_MAP = {
                        'dine_in': Order.Ordertype.DINE_IN,
                        'pick_up': Order.Ordertype.CARRY_OUT,
                        'delivery': Order.Ordertype.DELIVERY,
                    }
                    mapped_ot = ORDER_TYPE_MAP.get(raw_type)
                    if mapped_ot and mapped_ot != order.order_type:
                        order.order_type = mapped_ot
                        order.save(update_fields=['order_type'])
                # Capture card fields only if credit card chosen; otherwise store blanks.
                card_name = request.POST.get("card_name", "") if pm == Transaction.Method.CREDIT_CARD else ""
                card_number = request.POST.get("card_number", "") if pm == Transaction.Method.CREDIT_CARD else ""
                exp_date_val = None
                if pm == Transaction.Method.CREDIT_CARD:
                    raw_exp = request.POST.get("exp_date")
                    if raw_exp:
                        from datetime import datetime
                        try:
                            exp_date_val = datetime.strptime(raw_exp, "%Y-%m-%d").date()
                        except Exception:
                            exp_date_val = None
                cvv = request.POST.get("cvv", "") if pm == Transaction.Method.CREDIT_CARD else ""
                txn = Transaction(
                    order=order,
                    payment_method=pm,
                    card_name=card_name,
                    card_number=card_number,
                    exp_date=exp_date_val,
                    cvv=cvv,
                )
                txn.save()
                order.status = Order.Status.COMPLETED
                order.save()
                # Fully clear cart-related session state so sidebar resets.
                _reset_cart_session(request.session)
                request.session["cart_items"] = []  # explicit empty list (sidebar JS may expect it)
                request.session.modified = True
                request.session["last_order_id"] = order.id
        except Exception:
            # Fail open: still try to redirect.
            pass
        return redirect("menu:checkout_success")

    # GET: show current cart snapshot
    cart_items = request.session.get("cart_items", [])
    order_obj = None
    cart_order_id = request.session.get("cart_order_id")
    if cart_order_id:
        try:
            order_obj = Order.objects.prefetch_related("items__item").get(pk=cart_order_id)
            # reconcile order type from session if not yet persisted
            raw_type = request.session.get('order_type_raw')
            if raw_type:
                ORDER_TYPE_MAP = {
                    'dine_in': Order.Ordertype.DINE_IN,
                    'pick_up': Order.Ordertype.CARRY_OUT,
                    'delivery': Order.Ordertype.DELIVERY,
                }
                mapped_ot = ORDER_TYPE_MAP.get(raw_type)
                if mapped_ot and mapped_ot != order_obj.order_type:
                    order_obj.order_type = mapped_ot
                    order_obj.save(update_fields=['order_type'])
            # rebuild cart_items for template convenience
            rebuilt = []
            for oi in order_obj.items.all():
                image_url = None
                if getattr(oi.item, "menu_img", None):
                    try:
                        image_url = oi.item.menu_img.url
                    except Exception:
                        image_url = None
                toppings_list = []
                if oi.meat_topping:
                    toppings_list.append(oi.meat_topping)
                if oi.extra_toppings:
                    extras = [t.strip() for t in oi.extra_toppings.split(',') if t.strip()]
                    toppings_list.extend(extras)
                rebuilt.append({
                    "item_id": oi.item.item_id,
                    "name": oi.item.name,
                    "price": oi.price,
                    "quantity": oi.quantity,
                    "subtotal": oi.subtotal,
                    "image_url": image_url,
                    "toppings": toppings_list,
                })
            cart_items = rebuilt
        except Order.DoesNotExist:
            order_obj = None
    order_ctx = order_obj or request.session.get(
        "order", {"delivery": 0, "subtotal": 0, "total": 0, "items_count": 0}
    )
    return render(
        request,
        "checkout.html",
        {
            "cart_items": cart_items,
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

    # Persist a cart-order in DB and sync items so the sidebar cart is stored server-side
    order = Order.get_or_create_cart(request.user if request.user.is_authenticated else None, request.session)
    order.sync_items_from_cart(normalized)

    # Map frontend order type (dine_in | pick_up | delivery) to model choices ("dine in" | "carry out" | "delivery")
    ORDER_TYPE_MAP = {
        'dine_in': Order.Ordertype.DINE_IN,
        'pick_up': Order.Ordertype.CARRY_OUT,
        'delivery': Order.Ordertype.DELIVERY,
    }
    mapped = ORDER_TYPE_MAP.get(raw_order_type)
    if mapped and mapped != order.order_type:
        order.order_type = mapped
        order.save(update_fields=['order_type'])
    if raw_order_type:
        request.session['order_type_raw'] = raw_order_type
        request.session.modified = True

    return JsonResponse({'ok': True, 'count': len(normalized), 'cart_order_id': order.id, 'order_type': order.order_type})


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

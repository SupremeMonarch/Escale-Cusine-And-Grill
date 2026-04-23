from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from decimal import Decimal
from .models import MenuCategory, MenuSubCategory, MenuItem, Promotion,Order, OrderItem, Transaction, Delivery, Takeout,TOPPING_PRICES, eligible_for_toppings
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


def menu_mobile_page(request):
    return render(request, "menu_mobile.html")


def menu_mobile_data(request):
    """Return menu grouped by category/subcategory for mobile clients (jQuery/Flet)."""
    categories_qs = MenuCategory.objects.prefetch_related(
        "menusubcategory_set__menuitem_set"
    ).all()

    categories = []
    for category in categories_qs:
        subcategories = []
        for sub in category.menusubcategory_set.all():
            items = []
            for item in sub.menuitem_set.filter(is_available=True):
                image_url = ""
                if item.menu_img:
                    try:
                        image_url = request.build_absolute_uri(item.menu_img.url)
                    except Exception:
                        image_url = ""

                items.append(
                    {
                        "item_id": item.item_id,
                        "name": item.name,
                        "desc": item.desc,
                        "price": str(item.price),
                        "image_url": image_url,
                    }
                )

            if items:
                subcategories.append(
                    {
                        "subcategory": sub.subcategory,
                        "items": items,
                    }
                )

        if subcategories:
            categories.append(
                {
                    "category": category.category,
                    "slug": category.slug,
                    "subcategories": subcategories,
                }
            )

    return JsonResponse({"categories": categories})


@csrf_exempt
def mobile_checkout_start(request):
    """Create an in-progress order from JSON payload and return checkout URL.

    Payload:
    {
      "items": [{"item_id": 1, "quantity": 2, "meat_topping": "Chicken", "extra_toppings": []}],
      "order_type": "dine_in" | "pick_up" | "delivery"
    }
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    raw_items = payload.get("items") or []
    raw_order_type = payload.get("order_type") or "dine_in"

    normalized = []
    for it in raw_items:
        try:
            iid = int(it.get("item_id")) if it.get("item_id") is not None else None
        except Exception:
            iid = None
        if iid is None:
            continue
        qty = int(it.get("quantity", 1) or 1)
        if qty < 1:
            continue
        meat = it.get("meat_topping") or ""
        extras = it.get("extra_toppings") or []
        if not isinstance(extras, list):
            extras = []
        normalized.append(
            {
                "item_id": iid,
                "quantity": qty,
                "meat_topping": meat,
                "extra_toppings": extras,
            }
        )

    if not normalized:
        return JsonResponse({"ok": False, "error": "empty cart"}, status=400)

    ORDER_TYPE_MAP = {
        "dine_in": Order.Ordertype.DINE_IN,
        "pick_up": Order.Ordertype.CARRY_OUT,
        "delivery": Order.Ordertype.DELIVERY,
    }
    mapped_ot = ORDER_TYPE_MAP.get(raw_order_type, Order.Ordertype.DINE_IN)

    try:
        with db_transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                order_type=mapped_ot,
                status=Order.Status.IN_PROGRESS,
            )

            menu_items = {
                m.item_id: m
                for m in MenuItem.objects.filter(item_id__in=[x["item_id"] for x in normalized], is_available=True)
            }
            for x in normalized:
                menu_item = menu_items.get(x["item_id"])
                if not menu_item:
                    continue
                OrderItem.objects.create(
                    order=order,
                    item=menu_item,
                    quantity=x["quantity"],
                    meat_topping=x["meat_topping"],
                    extra_toppings=",".join([e for e in x["extra_toppings"] if e]),
                )

            if mapped_ot == Order.Ordertype.DELIVERY:
                Delivery.objects.create(order=order, address="TBD", fee=DELIVERY_FEE)
            elif mapped_ot == Order.Ordertype.CARRY_OUT:
                Takeout.objects.create(order=order, fee=TAKEOUT_FEE)

            order.update_total()

            Transaction.objects.create(
                order=order,
                payment_method=Transaction.Method.CREDIT_CARD,
                status=Transaction.Status.IN_PROGRESS,
            )
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

    checkout_url = request.build_absolute_uri(f"/menu/checkout/?order_id={order.id}")
    return JsonResponse({"ok": True, "order_id": order.id, "checkout_url": checkout_url})


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
        order_id = request.session.get('checkout_order_id') or request.POST.get('order_id')
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
    requested_order_id = request.GET.get('order_id')
    order_id = request.session.get('checkout_order_id') or requested_order_id
    order = None

    if order_id:
        try:
            order = Order.objects.get(pk=order_id, status=Order.Status.IN_PROGRESS)
            request.session['checkout_order_id'] = order.id
            request.session.modified = True
        except Order.DoesNotExist:
            order = None

    # If no order exists, we'll show preview from session (create on first visit)
    sess_cart = request.session.get("cart_items", [])

    if not order and not sess_cart:
        # Empty cart, redirect to menu
        return redirect("menu:menu_starters")

    rebuilt = []
    subtotal_sum = Decimal("0.00")
    items_count = 0

    if order:
        order_items = order.items.select_related('item').all()
        for oi in order_items:
            items_count += oi.quantity
            subtotal_sum += oi.subtotal
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
                toppings_list.extend([t.strip() for t in oi.extra_toppings.split(',') if t.strip()])
            rebuilt.append({
                "item_id": oi.item.item_id,
                "name": oi.item.name,
                "price": oi.price,
                "quantity": oi.quantity,
                "subtotal": oi.subtotal,
                "image_url": image_url,
                "toppings": toppings_list,
            })

        if order.order_type == Order.Ordertype.DELIVERY:
            raw_type = 'delivery'
            delivery_fee = order.delivery_fee
            fee_label = 'Delivery'
        elif order.order_type == Order.Ordertype.CARRY_OUT:
            raw_type = 'pick_up'
            delivery_fee = order.takeout_fee
            fee_label = 'Take Out'
        else:
            raw_type = 'dine_in'
            delivery_fee = Decimal("0.00")
            fee_label = 'Dine In'
        type_label = order.get_order_type_display()
    else:
        item_ids = [int(x.get('item_id')) for x in sess_cart if x.get('item_id')]
        items_map = {m.item_id: m for m in MenuItem.objects.filter(item_id__in=item_ids)} if item_ids else {}

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
        "order_id": order.id if order else None,
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



from rest_framework import viewsets, permissions
from .serializers import (
    MenuCategorySerializer, MenuSubCategorySerializer, MenuItemSerializer,
    PromotionSerializer, OrderSerializer, OrderItemSerializer,
    TransactionSerializer, DeliverySerializer, TakeoutSerializer, OrderCreateSerializer
)

# API ViewSets
class MenuCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer

class MenuSubCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuSubCategory.objects.all()
    serializer_class = MenuSubCategorySerializer

class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuItem.objects.filter(is_available=True)
    serializer_class = MenuItemSerializer

class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer  # POST — full order creation
        return OrderSerializer            # GET — read with nested items/delivery/etc

class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(order__user=self.request.user)

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(order__user=self.request.user)

class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Delivery.objects.filter(order__user=self.request.user)

class TakeoutViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TakeoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Takeout.objects.filter(order__user=self.request.user)

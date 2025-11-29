from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from datetime import timedelta
    
def default_arrival_time():
    return (timezone.now() + timedelta(minutes=15)).time() #adds 15 min to current time when entering a default arrival time for delivery

def roundup(val):
    return Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) #makes 1.555 become 1.56

# Server-side topping pricing to mirror frontend sidebar.js
TOPPING_PRICES = {
    "Eggs": Decimal("25"),
    "Chicken": Decimal("0"),
    "Shrimps": Decimal("30"),
    "Beef": Decimal("15"),
    "Lamb": Decimal("30"),
    "Mushrooms": Decimal("20"),
}

def eligible_for_toppings(item_name: str) -> bool:
    if not item_name:
        return False
    name = str(item_name).lower()
    return (
        "fried rice" in name
        or "fried noodles" in name
        or "magic bowl" in name
    )

class MenuCategory(models.Model):
    category = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.category


class MenuSubCategory(models.Model):
    subcategory = models.CharField(max_length=100)
    category_id = models.ForeignKey(MenuCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.subcategory

class MenuItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    desc = models.TextField(max_length=300)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    menu_img = models.ImageField(upload_to="menu_images/", max_length=300)  # ← UPDATED
    is_available = models.BooleanField()
    subcategory_id = models.ForeignKey(MenuSubCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name    

class Promotion(models.Model):
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="promotions")
    title = models.CharField(max_length=100)
    desc = models.TextField(max_length=300)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    discountpercent = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    def save(self, *args, **kwargs):
        # ensure start_date <= end_date
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("end date cannot be before start date")
        super().save(*args, **kwargs)
    
    def __str__(self): #this is so only the user's name appears on the admin page when an order is added
        return self.title
    
class Order(models.Model):
    # allow anonymous orders by permitting a NULL user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True, editable=False)
    order_id_str = models.CharField(max_length=20, unique=True, blank=True) #This a unique, human-readable ID
    #table_id = models.ForeignKey(Table, on_delete=models.PROTECT) not yet created models.py for Table

    class Ordertype(models.TextChoices): #enum data type
        DELIVERY =  "delivery", "Delivery"
        CARRY_OUT   =   "pick up", "Pick Up"
        DINE_IN =  "dine in", "Dine In",

    order_type = models.CharField(
        max_length=20,
        choices=Ordertype.choices,
    )
    class Status(models.TextChoices): #enum data type
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED   = "completed",   "Completed"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    # Persisted monetary fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])

    # Auto-generate the human-readable order_id_str on save
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        update_fields = kwargs.get('update_fields')
        
        super().save(*args, **kwargs) # Save first to get a primary key (self.id)
        if not self.order_id_str:
            self.order_id_str = f"ORD-{self.id:03d}"
            super(Order, self).save(update_fields=['order_id_str'])
        
        # Handle order_type changes and create/delete Delivery/Takeout accordingly
        # Only run this when it's not a new order AND we're not in the middle of updating specific fields
        if not is_new and update_fields is None:
            self.update_total_with_type()


    def __str__(self): # readable representation for admin
        # prefer the generated order id when available
        if self.order_id_str:
            return self.order_id_str
        return f"{self.user}'s Order"

    def update_total(self, save=True):
        sumofitems = self.items.aggregate(s=Sum("subtotal"))["s"] or Decimal("0.00")  # sums up all subtotals for an order
        try:
            delivery_fee = self.delivery.fee
        except Delivery.DoesNotExist:
            delivery_fee = Decimal("0.00")
        # include takeout fee when applicable (mutually exclusive with delivery)
        try:
            takeout_fee = self.takeout.fee
        except Exception:
            takeout_fee = Decimal("0.00")
        applied_fee = delivery_fee if delivery_fee else takeout_fee
        # update persisted fields
        self.subtotal = roundup(sumofitems)
        new_total = roundup(sumofitems + applied_fee)  # adds service fee if there is one
        self.total = new_total
        if save:
            self.save(update_fields=["subtotal", "total"])
        return self.total

    def update_total_with_type(self):
        """Handle order_type changes and sync Delivery/Takeout records accordingly."""
        # Import locally to avoid circular dependency since these are defined later in the file
        from apps.menu import models as menu_models
        
        if self.order_type == self.Ordertype.DELIVERY:
            # Ensure Delivery exists, remove Takeout
            try:
                self.takeout.delete()
            except menu_models.Takeout.DoesNotExist:
                pass
            except Exception:
                pass
            try:
                self.delivery
            except menu_models.Delivery.DoesNotExist:
                menu_models.Delivery.objects.create(order=self, address="", fee=Decimal("100.00"))
        elif self.order_type == self.Ordertype.CARRY_OUT:
            # Ensure Takeout exists, remove Delivery
            try:
                self.delivery.delete()
            except menu_models.Delivery.DoesNotExist:
                pass
            except Exception:
                pass
            try:
                self.takeout
            except menu_models.Takeout.DoesNotExist:
                menu_models.Takeout.objects.create(order=self, fee=Decimal("50.00"))
        else:  # DINE_IN
            # Remove both Delivery and Takeout
            try:
                self.delivery.delete()
            except menu_models.Delivery.DoesNotExist:
                pass
            except Exception:
                pass
            try:
                self.takeout.delete()
            except menu_models.Takeout.DoesNotExist:
                pass
            except Exception:
                pass
        
        # Recalculate total after order_type changes
        self.update_total()

    # NOTE: subtotal is now a stored field on the model

    @property
    def items_count(self):
        """Total quantity across all order items."""
        return self.items.aggregate(c=Sum("quantity"))["c"] or 0

    @property
    def delivery_fee(self):
        try:
            return self.delivery.fee
        except Delivery.DoesNotExist:
            return Decimal("0.00")

    @property
    def takeout_fee(self):
        try:
            return self.takeout.fee
        except Exception:
            return Decimal("0.00")

    def sync_items_from_cart(self, cart_items, save=True):
        """Sync OrderItems to match a cart_items list.

        cart_items: list of dicts [{'item_id': int, 'quantity': int, 'meat_topping': str, 'extra_toppings': [..]}, ...]
        Items are keyed by (item_id, meat_topping, sorted extras signature) so the same dish with different
        toppings becomes distinct OrderItem rows.
        Returns a tuple (created_count, updated_count, removed_count).
        """
        created = 0
        updated = 0
        removed = 0

        def signature(item_id, meat, extras):
            extras_sig = ",".join(sorted([e for e in extras if e]))
            meat_sig = meat or ""
            return f"{item_id}|{meat_sig}|{extras_sig}"

        incoming_structs = []
        for x in cart_items:
            if not x.get('item_id'):
                continue
            iid = int(x['item_id'])
            qty = int(x.get('quantity', 1) or 1)
            meat = x.get('meat_topping') or ''
            extras = x.get('extra_toppings') or []
            if not isinstance(extras, list):
                extras = []
            incoming_structs.append({'item_id': iid, 'quantity': qty, 'meat': meat, 'extras': extras})

        incoming_map = {signature(s['item_id'], s['meat'], s['extras']): s for s in incoming_structs}

        existing_items = list(self.items.select_related('item').all())
        existing_map = {signature(oi.item_id, oi.meat_topping, [e.strip() for e in oi.extra_toppings.split(',') if e.strip()]): oi for oi in existing_items}

        # create or update
        for sig, data in incoming_map.items():
            iid = data['item_id']
            qty = data['quantity']
            meat = data['meat']
            extras_list = data['extras']
            extras_text = ",".join([e for e in extras_list if e])
            if sig in existing_map:
                oi = existing_map[sig]
                if oi.quantity != qty:
                    oi.quantity = qty
                    oi.save()
                    updated += 1
            else:
                try:
                    menu_item = MenuItem.objects.get(pk=iid)
                except MenuItem.DoesNotExist:
                    continue
                OrderItem.objects.create(
                    order=self,
                    item=menu_item,
                    quantity=qty,
                    meat_topping=meat,
                    extra_toppings=extras_text,
                )
                created += 1

        # remove items not present anymore
        for sig, oi in existing_map.items():
            if sig not in incoming_map:
                oi.delete()
                removed += 1

        if save:
            self.update_total()

        return (created, updated, removed)

    @classmethod
    def get_or_create_cart(cls, request_user, session):
        """Return an IN_PROGRESS Order for the session/user, creating one if needed.

        If `session` contains 'cart_order_id' that order will be returned when valid.
        Otherwise a new Order is created and its id saved into `session['cart_order_id']`.
        """
        order = None
        cart_order_id = session.get('cart_order_id')
        if cart_order_id:
            try:
                order = cls.objects.get(pk=cart_order_id)
            except cls.DoesNotExist:
                order = None

        if not order:
            order = cls.objects.create(user=request_user if request_user and request_user.is_authenticated else None,
                                       order_type=cls.Ordertype.DELIVERY,
                                       status=cls.Status.IN_PROGRESS)
            session['cart_order_id'] = order.id
            session.modified = True

        return order


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=Decimal("0.00"))
    promo = models.ForeignKey(
        Promotion,
        null=True,           # DB can store NULL
        blank=True,          # forms/admin can leave it empty
        on_delete=models.SET_NULL,  # keep the order item if promo is deleted
    )
    meat_topping = models.CharField(max_length=50, blank=True, help_text="Selected meat topping if applicable.")
    extra_toppings = models.TextField(blank=True, help_text="Comma-separated list of extra toppings.")

    def save(self, *args, **kwargs):
        unit = self.item.price
        if self.promo:
            # only apply if promo is active AND for this item
            now = timezone.now()
            if self.promo.item_id == self.item_id and self.promo.start_date <= now <= self.promo.end_date:
                unit = unit * (Decimal("1") - self.promo.discountpercent)
        # add topping prices if applicable
        extra_charge = Decimal("0.00")
        if eligible_for_toppings(getattr(self.item, "name", "")):
            # meat topping
            if self.meat_topping:
                extra_charge += TOPPING_PRICES.get(self.meat_topping, Decimal("0.00"))
            # extra toppings (comma-separated)
            if self.extra_toppings:
                for t in [x.strip() for x in self.extra_toppings.split(',') if x.strip()]:
                    extra_charge += TOPPING_PRICES.get(t, Decimal("0.00"))

        self.price = roundup(unit + extra_charge)
        self.subtotal = roundup(self.price * self.quantity)
        super().save(*args, **kwargs)
        self.order.update_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()

    def __str__(self): #this is so only the user's name appears on the admin page when an order is added
        return f"{self.quantity} x {self.item.name}(s)"
    
    @property
    def discounted_price(self):
        """
        Returns discounted price if an active promotion exists. Mostly used in views.py since it is not actually a value stored in the db.
        """
        if not self.promo:
            return self.item.price
        discounted = self.item.price * (Decimal("1") - self.promo.discountpercent)
        return roundup(discounted)

class Delivery(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="delivery")
    address = models.TextField(max_length=300)
    fee = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))], default=Decimal("50.00"))
    class Status(models.TextChoices): #enum data type
        PREPARING_ORDER = "preparing_order" , "Preparing Order"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED   = "delivered",   "Delivered"
    
    delivery_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PREPARING_ORDER,
    )
    arrival_time = models.TimeField(null=True, blank=True, default=default_arrival_time)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # recalc order total whenever delivery is created/edited
        if self.order_id:
            self.order.update_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()

    def __str__(self): #this is so only the user's name appears on the admin page when an order is added
        return f"{self.order.user}'s Delivery"

class Takeout(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="takeout")
    fee = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))], default=Decimal("50.00"))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.order_id:
            self.order.update_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()

    def __str__(self):
        return f"{self.order.user}'s Takeout"

class Transaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    class Method(models.TextChoices): #enum data type
        CREDIT_CARD = "credit_card" , "Credit_Card"
        JUICE = "juice", "Juice"
        MYT_MOB   = "mytmob",   "MyTMob"
        PAYPAL = "paypal" , "PayPal"
    payment_method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.CREDIT_CARD,
    )
    # Card details (only required/used when payment_method == CREDIT_CARD)
    card_name = models.CharField(max_length=100, blank=True)
    card_number = models.CharField(max_length=19, blank=True, help_text="PAN without spaces, typically 13-19 digits")
    exp_date = models.DateField(null=True, blank=True)
    cvv = models.CharField(max_length=4, blank=True)
    transaction_date = models.DateTimeField(auto_now_add=True, editable=False)  
    class Status(models.TextChoices): #enum data type
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED   = "completed",   "Completed"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    def clean(self):
        """Validation intentionally disabled (all inputs accepted)."""
        return

    def save(self, *args, **kwargs):
        # Skip full_clean to avoid any validation; just copy order total.
        self.amount = roundup(self.order.total)
        super().save(*args, **kwargs)

    def __str__(self): #this is so only the user's name appears on the admin page when an order is added
        return f"{self.order.user}'s Transaction"
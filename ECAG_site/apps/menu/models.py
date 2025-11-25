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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True, editable=False)
    order_id_str = models.CharField(max_length=20, unique=True, blank=True) #This a unique, human-readable ID
    #table_id = models.ForeignKey(Table, on_delete=models.PROTECT) not yet created models.py for Table

    class Ordertype(models.TextChoices): #enum data type
        DELIVERY =  "delivery", "Delivery"
        CARRY_OUT   =   "carry out", "Carry Out"
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
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])

    # Auto-generate the human-readable order_id_str on save
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) # Save first to get a primary key (self.id)
        if not self.order_id_str:
            self.order_id_str = f"ORD-{self.id:03d}"
            super(Order, self).save(update_fields=['order_id_str'])


    def __str__(self): #this is so only the user's name appears on the admin page when an order is added
        return f"{self.user}'s Order"

    def update_total(self, save=True):
        sumofitems = self.items.aggregate(s=Sum("subtotal"))["s"] or Decimal("0.00") #sums up all subtotals for an order
        try:
            delivery_fee = self.delivery.fee
        except Delivery.DoesNotExist:
            delivery_fee = Decimal("0.00")
        new_total = roundup(sumofitems + delivery_fee) #adds delivery fee if there is one
        self.total = new_total
        if save:
            self.save(update_fields=["total"])
        return self.total


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

    def save(self, *args, **kwargs):
        unit = self.item.price
        if self.promo:
            # only apply if promo is active AND for this item
            now = timezone.now()
            if self.promo.item_id == self.item_id and self.promo.start_date <= now <= self.promo.end_date:
                unit = unit * (Decimal("1") - self.promo.discountpercent)
        self.price = roundup(unit)
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

class Transaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    class Method(models.TextChoices): #enum data type
        CREDIT_CARD = "credit_card" , "Credit_Card"
        JUICE = "juice", "Juice"
        MYT_MOB   = "mytmob",   "MyTMob"
    payment_method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.CREDIT_CARD,
    )
    transaction_date = models.DateTimeField(auto_now_add=True, editable=False)  
    class Status(models.TextChoices): #enum data type
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED   = "completed",   "Completed"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    def save(self, *args, **kwargs):
        self.amount = roundup(self.order.total)
        super().save(*args, **kwargs)

    def __str__(self): #this is so only the user's name appears on the admin page when an order is added
        return f"{self.order.user}'s Transaction"
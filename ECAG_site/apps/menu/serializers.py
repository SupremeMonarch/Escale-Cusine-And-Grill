from django.utils import timezone
from rest_framework import serializers

from .models import (
    Delivery,
    MenuCategory,
    MenuItem,
    MenuSubCategory,
    Order,
    OrderItem,
    Promotion,
    TOPPING_PRICES,
    Takeout,
    Transaction,
    eligible_for_toppings,
)


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = ["id", "category", "slug"]


class MenuSubCategorySerializer(serializers.ModelSerializer):
    category = MenuCategorySerializer(source="category_id", read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=MenuCategory.objects.all())

    class Meta:
        model = MenuSubCategory
        fields = ["id", "subcategory", "category_id", "category"]


class MenuItemSerializer(serializers.ModelSerializer):
    subcategory = MenuSubCategorySerializer(source="subcategory_id", read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(queryset=MenuSubCategory.objects.all())

    class Meta:
        model = MenuItem
        fields = [
            "item_id",
            "name",
            "desc",
            "price",
            "menu_img",
            "is_available",
            "subcategory_id",
            "subcategory",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Item name is required.")
        return value

    def validate_desc(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Item description is required.")
        return value


class PromotionSerializer(serializers.ModelSerializer):
    item = MenuItemSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all(), source="item")

    class Meta:
        model = Promotion
        fields = [
            "id",
            "item_id",
            "item",
            "title",
            "desc",
            "start_date",
            "end_date",
            "discountpercent",
        ]

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Promotion title is required.")
        return value

    def validate_desc(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Promotion description is required.")
        return value

    def validate_discountpercent(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError("Discount must be between 0 and 1 (for example: 0.15 for 15%).")
        return value

    def validate(self, attrs):
        start_date = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end_date = attrs.get("end_date") or getattr(self.instance, "end_date", None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})

        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    item = MenuItemSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all(), source="item")
    promo_id = serializers.PrimaryKeyRelatedField(
        queryset=Promotion.objects.all(), source="promo", required=False, allow_null=True
    )
    toppings_list = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "item_id",
            "item",
            "quantity",
            "price",
            "subtotal",
            "promo_id",
            "meat_topping",
            "extra_toppings",
            "toppings_list",
        ]
        read_only_fields = ["price", "subtotal"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate(self, attrs):
        item = attrs.get("item") or getattr(self.instance, "item", None)
        meat_topping = attrs.get("meat_topping")
        extra_toppings = attrs.get("extra_toppings")

        if meat_topping is None and self.instance is not None:
            meat_topping = self.instance.meat_topping
        if extra_toppings is None and self.instance is not None:
            extra_toppings = self.instance.extra_toppings

        meat_topping = (meat_topping or "").strip()
        extras = [x.strip() for x in (extra_toppings or "").split(",") if x.strip()]

        if not eligible_for_toppings(getattr(item, "name", "")):
            if meat_topping or extras:
                raise serializers.ValidationError(
                    "Toppings are only allowed for Fried Rice, Fried Noodles, and Magic Bowl items."
                )
            return attrs

        allowed_toppings = set(TOPPING_PRICES.keys())

        if meat_topping and meat_topping not in allowed_toppings:
            raise serializers.ValidationError({"meat_topping": "Invalid meat topping selected."})

        invalid_extras = [x for x in extras if x not in allowed_toppings]
        if invalid_extras:
            raise serializers.ValidationError(
                {"extra_toppings": f"Invalid topping(s): {', '.join(invalid_extras)}"}
            )

        return attrs


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ["id", "order", "address", "fee", "delivery_status", "arrival_time"]

    def validate_address(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Delivery address is required.")
        return value


class TakeoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Takeout
        fields = ["id", "order", "fee", "pickup_status"]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "order",
            "amount",
            "payment_method",
            "card_name",
            "card_number",
            "exp_date",
            "cvv",
            "transaction_date",
            "status",
        ]
        read_only_fields = ["amount", "transaction_date"]

    def validate(self, attrs):
        payment_method = attrs.get("payment_method") or getattr(self.instance, "payment_method", None)

        if payment_method == Transaction.Method.CREDIT_CARD:
            missing = []
            for field in ["card_name", "card_number", "exp_date", "cvv"]:
                value = attrs.get(field)
                if value is None and self.instance is not None:
                    value = getattr(self.instance, field, None)
                if not value:
                    missing.append(field)
            if missing:
                raise serializers.ValidationError(
                    {field: "This field is required for credit card payments." for field in missing}
                )

            exp_date = attrs.get("exp_date") or getattr(self.instance, "exp_date", None)
            if exp_date and exp_date < timezone.now().date():
                raise serializers.ValidationError({"exp_date": "Card expiration date cannot be in the past."})
        else:
            attrs["card_name"] = ""
            attrs["card_number"] = ""
            attrs["exp_date"] = None
            attrs["cvv"] = ""

        return attrs


class OrderSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source="user_id")
    items = OrderItemSerializer(many=True, read_only=True)
    delivery = DeliverySerializer(read_only=True)
    takeout = TakeoutSerializer(read_only=True)
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id_str",
            "user",
            "user_id",
            "order_date",
            "order_type",
            "status",
            "subtotal",
            "total",
            "items_count",
            "delivery_fee",
            "takeout_fee",
            "items",
            "delivery",
            "takeout",
            "transactions",
        ]
        read_only_fields = [
            "order_id_str",
            "order_date",
            "subtotal",
            "total",
            "items_count",
            "delivery_fee",
            "takeout_fee",
        ]

    def validate_order_type(self, value):
        valid_values = {choice[0] for choice in Order.Ordertype.choices}
        if value not in valid_values:
            raise serializers.ValidationError("Invalid order type.")
        return value

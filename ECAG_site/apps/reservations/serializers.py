from datetime import datetime, time as dt_time, timedelta

from rest_framework import serializers

from .models import Reservation, Table


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = [
            "table_id",
            "table_number",
            "seats",
            "qr_code",
            "x_position",
            "y_position",
        ]


class ReservationSerializer(serializers.ModelSerializer):
    table = TableSerializer(source="table_id", read_only=True)
    table_id = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all())

    class Meta:
        model = Reservation
        fields = [
            "reservation_id",
            "user_id",
            "table_id",
            "table",
            "date",
            "time",
            "guest_count",
            "full_name",
            "phone",
            "email",
            "special_requests",
            "status",
            "created_at",
        ]
        read_only_fields = ["reservation_id", "user_id", "created_at"]

    def validate_date(self, value):
        if value < datetime.now().date():
            raise serializers.ValidationError("Requested date is in the past.")
        return value

    def validate_time(self, value):
        open_time = dt_time(15, 0)
        last_start = dt_time(22, 0)
        if not (open_time <= value <= last_start):
            raise serializers.ValidationError(
                "Restaurant is open 15:00-23:00; last booking start is 22:00."
            )
        if value.minute % 15 != 0:
            raise serializers.ValidationError(
                "Time must be in 15-minute increments (00, 15, 30, 45)."
            )
        return value

    def validate_guest_count(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError("Guest count must be between 1 and 20.")
        return value

    def validate(self, attrs):
        table = attrs.get("table_id") or getattr(self.instance, "table_id", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)
        time = attrs.get("time") or getattr(self.instance, "time", None)
        guest_count = attrs.get("guest_count") or getattr(self.instance, "guest_count", None)

        if table and guest_count:
            expected_seats = 2 if guest_count <= 2 else 4
            if table.seats != expected_seats:
                raise serializers.ValidationError(
                    {"table_id": "Selected table cannot accommodate the party size."}
                )

        if table and date and time:
            req_start = datetime.combine(date, time)
            req_end = req_start + timedelta(hours=2)

            existing = Reservation.objects.filter(table_id=table, date=date).exclude(
                status="cancelled"
            )
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)

            for reservation in existing:
                current_start = datetime.combine(reservation.date, reservation.time)
                current_end = current_start + timedelta(hours=2)
                if not (req_end <= current_start or req_start >= current_end):
                    raise serializers.ValidationError(
                        {"table_id": "Table is not available for the requested slot."}
                    )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")

        validated_data["user_id"] = request.user
        return super().create(validated_data)

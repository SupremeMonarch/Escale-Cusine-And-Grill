from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import qrcode

class Table(models.Model):
    table_id = models.AutoField(primary_key=True)
    table_number = models.IntegerField(unique=True)
    seats = models.IntegerField(choices=[(2, '2 seats'), (4, '4 seats')])
    qr_code = models.CharField(max_length=100, unique=True)
    x_position = models.IntegerField()
    y_position = models.IntegerField()

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'Table {self.table_number}')
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        img_path = f'media/qr_codes/table_{self.table_number}.png'
        img.save(img_path)
        self.qr_code = img_path
        self.save()

    def is_available(self, date, time):
        return not Reservation.objects.filter(table_id=self, date=date, time=time, status='confirmed').exists()

    def get_table_status(self):
        return {
            'table_number': self.table_number,
            'seats': self.seats,
            'qr_code': self.qr_code,
            'x_position': self.x_position,
            'y_position': self.y_position
        }

    def __str__(self):
        return f"Table {self.table_number} ({self.seats} seats)"

class Reservation(models.Model):
    reservation_id = models.AutoField(primary_key=True)
    user_id =  models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    table_id = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    date = models.DateField()
    time = models.TimeField()
    guest_count = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('seated', 'Seated'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no-show', 'No-show'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time'] # Order by upcoming

    def confirm_reservation(self):
        self.status = 'confirmed'
        self.save()

    def cancel_reservation(self):
        self.status = 'cancelled'
        self.save()

    def modify_reservation(self, date=None, time=None, guest_count=None):
        if date:
            self.date = date
        if time:
            self.time = time
        if guest_count:
            self.guest_count = guest_count
        self.save()

    def __str__(self):
        return f"Reservation {self.reservation_id} for User {self.user_id} on {self.date} at {self.time}"

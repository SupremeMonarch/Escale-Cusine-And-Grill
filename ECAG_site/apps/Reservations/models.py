from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Reservation(models.Model):

    reservation_id = models.AutoField(max_length=10,unique=True, primary_key=True)
    user_id =  models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='reservations')
    table_id = models.CharField(max_length=10)
    date = models.DateField()
    time = models.TimeField()
    guest_count = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')])
    created_at = models.DateTimeField(auto_now_add=True)

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
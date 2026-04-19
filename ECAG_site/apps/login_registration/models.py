from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link to the User model
    phone_regex = RegexValidator(
                                    regex=r'^(?:\+230|230|0)?5\d{7}$',
                                    message="Enter a valid Mauritian mobile number (e.g. 5XXXXXXX or +2305XXXXXXX)."
                                )
    address = models.CharField(max_length=50, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=20, null=True, blank=True)

    def __str__(self):
        return self.user.username

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

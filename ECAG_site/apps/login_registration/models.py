from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link to the User model
    phone_regex = RegexValidator(
                                    regex=r'^(?:\+230|230|0)?5\d{7}$',
                                    message="Enter a valid Mauritian mobile number (e.g. 5XXXXXXX or +2305XXXXXXX)."
                                )
    address=models.CharField(max_length=50,null=True)
    date_of_birth = models.DateField()
    phone_number=models.CharField(validators=[phone_regex],max_length=20)

    def __str__(self):
        return self.user.username 
    




# THIS WAS READJUSTED
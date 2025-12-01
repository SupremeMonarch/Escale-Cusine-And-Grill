from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password


# Create your models here.
class Customer(models.Model):
    Preference_Choices= (
                            ('A','A'),
                            ('B','B'),
                        )
    Role_Choices= (
                            ('Staff','Staff'),
                            ('Customer','Customer'),
                        )
    
    phone_regex = RegexValidator(
                                    regex=r'^(?:\+230|230|0)?5\d{7}$',
                                    message="Enter a valid Mauritian mobile number (e.g. 5XXXXXXX or +2305XXXXXXX)."
                                )
    email_regex=RegexValidator(
                                    regex=r'(?i)^[a-zA-Z1-9]+@(gmail|hotmail|umail)\.[a-zA-Z]$',
                                    message="Enter a valid Email."
                                )
    customer_id = models.AutoField(primary_key=True)
    First_Name=models.CharField(max_length=100,null=True)
    Last_Name=models.CharField(max_length=100,null=True)
    Preferences=models.CharField(max_length=10,choices=Preference_Choices)
    password = models.CharField(max_length=255)
    phone_number=models.CharField(validators=[phone_regex],max_length=20)
    role=models.CharField(max_length=10,choices=Role_Choices)
    email=models.CharField(validators=[email_regex],max_length=100,unique=True)
    date_joined=models.DateTimeField(auto_now_add=True,null=True)
    
    # HASH ONCE, SI HASH TWICE KK FANE
    def save(self, *args, **kwargs):
        # Hash password only when creating
        if not self.pk:  
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
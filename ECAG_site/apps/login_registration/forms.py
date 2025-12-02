from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import Customer
from django.contrib.auth.models import User

class CustomerRegistrationForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Confirm Password'})
    )

    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'date_of_birth', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Last Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Mobile Number'}),
            'email': forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Email'}),
            'password': forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Password'}, render_value=False),
            'address': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Address'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
    
class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile
from django.contrib.auth.forms import UserCreationForm

class CustomUserProfileForm(forms.ModelForm):

    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}), required=True)
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}), required=True)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}), required=True)
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))


    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    address = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'placeholder': 'Address'}))
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'date_of_birth']

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        
        username = cleaned_data.get('username')
        
        if User.objects.filter(username=username).exists():
            self.add_error('username', 'This username is already taken.')

        return cleaned_data

    def save(self, commit=True):

        user = User.objects.create_user(
                                            username=self.cleaned_data['username'],
                                            email=self.cleaned_data['email'],
                                            password=self.cleaned_data['password1'],
                                            first_name=self.cleaned_data['first_name'],
                                            last_name=self.cleaned_data['last_name']
                                        )


        user_profile = UserProfile(
                                        user=user,
                                        phone_number=self.cleaned_data['phone_number'],
                                        address=self.cleaned_data['address'],
                                        date_of_birth=self.cleaned_data['date_of_birth']
                                    )

        if commit:
            user_profile.save()

        return user_profile


class LoginForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

























# from django.forms import ModelForm
# from django.contrib.auth.forms import UserCreationForm
# from django import forms
# from .models import Customer
# from django.contrib.auth.models import User

# class CustomerRegistrationForm(forms.ModelForm):
#     confirm_password = forms.CharField(
#         widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Confirm Password'})
#     )

#     class Meta:
#         model = Customer
#         fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'date_of_birth', 'password']
#         widgets = {
#             'first_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'First Name'}),
#             'last_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Last Name'}),
#             'phone_number': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Mobile Number'}),
#             'email': forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Email'}),
#             'password': forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Password'}, render_value=False),
#             'address': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Address'}),
#             'date_of_birth': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
#         }

#     def clean(self):
#         cleaned_data = super().clean()
#         password = cleaned_data.get('password')
#         confirm_password = cleaned_data.get('confirm_password')
#         if password != confirm_password:
#             self.add_error('confirm_password', "Passwords do not match")
    
# class LoginForm(forms.Form):
#     email = forms.EmailField(label="Email")
#     password = forms.CharField(widget=forms.PasswordInput, label="Password")
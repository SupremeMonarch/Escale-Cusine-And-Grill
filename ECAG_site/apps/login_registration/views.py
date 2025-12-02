from django.shortcuts import render,redirect
from django.contrib import messages
from django.http import HttpResponse
from .forms import CustomerRegistrationForm, LoginForm
from django.contrib.auth.hashers import check_password,make_password
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login,logout
from .models import Customer

# v1 and v2
# def home(request):
#     # return HttpResponse("HomePage") v1
#     return render(request,'login_registration/page1.html') # v2

# v3
# def home(request):                                                          
#     # return HttpResponse("HomePage") v1                           
#     form=UserCreationForm()                                        
#     context={'form':form}                                           
#     return render(request,'login_registration/page1.html',context)

# # v4
# def home(request):                                                          
#     # return HttpResponse("HomePage") v1                           
#     form=UserCreationForm()

#     if request.method=="POST":
#         form=UserCreationForm(request.POST)
#         if form.is_valid():
#             form.save()
#     context={'form':form}                                           
#     return render(request,'login_registration/page1.html',context)

def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            customer = form.save()  # save() now automatically hashes password
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login_registration:login')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'login_registration/registration_page.html', {'form': form})
    
def contact(request):
    # return HttpResponse("Contact")
    return render(request,'login_registration/page2.html') # v2

def inheritor(request):
    # return HttpResponse("Contact")
    return render(request,'login_registration/inheritor.html')

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            password = form.cleaned_data["password"].strip()

            try:
                user = Customer.objects.get(email=email)
            except Customer.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return render(request, "login_registration/login.html", {"form": form})

            # Check hashed password manually
            if check_password(password, user.password):
                # Store user ID in session manually
                request.session["customer_id"] = user.customer_id
                request.session["customer_name"] = f"{user.first_name} {user.last_name}"

                messages.success(request, "Login successful!")
                return redirect('core:home')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, "login_registration/login.html", {"form": form})

def logout_view(request):
    if "customer_id" in request.session:
        del request.session["customer_id"]

    # Optional
    messages.success(request, "Logged out successfully.")

    return redirect("core:home")  
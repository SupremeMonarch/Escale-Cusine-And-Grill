from django.shortcuts import render,redirect
from django.contrib import messages
from django.http import HttpResponse
from .forms import CustomerRegistrationForm, LoginForm
from django.contrib.auth.hashers import check_password,make_password
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
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

def home(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            customer = form.save()  # save() now automatically hashes password
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'login_registration/page1.html', {'form': form})
    
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
            # Get and strip the data
            email = form.cleaned_data["email"].strip()
            password = form.cleaned_data["password"].strip()
            
            # # DEBUG: print form data
            # print("Email entered:", email)
            # print("Password entered:", password)
            
            try:
                # Case-insensitive lookup
                customer = Customer.objects.get(email__iexact=email)
                # print("Customer found:", customer)
                # print("Password hash in DB:", customer.password)
            except Customer.DoesNotExist:
                customer = None
                print("No customer found with that email")
            
            # Check password
            if customer and check_password(password, customer.password):
                print("Password check passed")
                request.session['customer_id'] = customer.customer_id
                messages.success(request, "Login successful!")
                return redirect("home")
            else:
                print("Password check failed")
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, "login_registration/login.html", {"form": form})


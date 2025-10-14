from django.shortcuts import render

def reservations(request):
    return render(request, "reservations/reservations.html")

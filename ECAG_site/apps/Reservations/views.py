from django.shortcuts import render

def reservations(request):
    context = {'step_number': 1}
    return render(request, "reservations/reservations.html", context)

def reservations_step2(request):
    context = {'step_number': 2}
    return render(request, "reservations/reservations_step2.html", context)

def reservations_step3(request):
    context = {'step_number': 3}
    return render(request, "reservations/reservations_step3.html", context)
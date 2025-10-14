from django.shortcuts import render

def menu_starters(request):
    return render(request, 'menu_starters.html')

def menu_main_course(request):
    return render(request, 'menu_main_course.html')

def menu_beverages(request):
    return render(request, 'menu_beverages.html')
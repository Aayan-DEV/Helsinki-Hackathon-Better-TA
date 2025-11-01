from django.shortcuts import render

def dashboard(request):
    return render(request, 'students_dash/students_dash.html')
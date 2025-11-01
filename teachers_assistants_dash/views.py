from django.shortcuts import render

def dashboard(request):
    return render(request, 'teachers_assistants_dash/teachers_assistants_dash.html')
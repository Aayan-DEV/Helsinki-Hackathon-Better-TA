from django.urls import path
from .views import ping_supabase

urlpatterns = [
    path('ping/', ping_supabase, name='teachers_dash_ping'),
]
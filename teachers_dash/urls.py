from django.urls import path
from .views import ping_supabase, dashboard, register_teacher, resend_confirmation_email, confirm_teacher_signup

urlpatterns = [
    path('', dashboard, name='teachers_dashboard_root'),  # /teachers/ → dashboard
    path('ping/', ping_supabase, name='teachers_dash_ping'),
    path('dashboard/', dashboard, name='teachers_dashboard'),
    path('register/', register_teacher, name='teachers_register'),
    path('resend-confirmation/', resend_confirmation_email, name='teachers_resend_confirmation'),
    path('confirm-signup/', confirm_teacher_signup, name='teachers_confirm_signup'),
]
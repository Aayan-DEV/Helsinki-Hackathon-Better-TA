from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from teachers_dash.views import dashboard as teachers_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        '',
        TemplateView.as_view(
            template_name='home/home.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='home',
    ),
    path('dashboard/teacher/', teachers_dashboard, name='teachers_dashboard_direct'),
    path('teachers/', include('teachers_dash.urls')),
    # Allauth routes
    path('accounts/', include('allauth.urls')),
    path(
        'auth/signup/',
        TemplateView.as_view(
            template_name='auth/global/signup/signup.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='global_signup',
    ),
    path(
        'auth/teachers/signup/',
        TemplateView.as_view(
            template_name='auth/teachers_auth/signup/signup.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='teachers_signup',
    ),
    path('dashboard/assistants/', include('teachers_assistants_dash.urls')),
    path('dashboard/students/', include('students_dash.urls')),

]
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from teachers_dash.views import dashboard as teachers_dashboard
from teachers_assistants_dash.views import (
    validate_ta_code,
    register_ta,
    resend_ta_confirmation,
    confirm_ta_signup,
)
from students_dash.views import (
    dashboard as students_dashboard,
    students_login_page,
    students_login_api,
)

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

    path(
        'auth/students/login/',
        students_login_page,
        name='students_login',
    ),
    path('students/auth/login/', students_login_api, name='students_auth_login'),
    path('dashboard/student/', students_dashboard, name='students_dashboard_direct'),

    path('teachers/', include('teachers_dash.urls')),

    path('students/', include('students_dash.urls')),

    path(
        'auth/login/',
        TemplateView.as_view(
            template_name='auth/global/login/login.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='global_login',
    ),

    path(
        'auth/teachers/login/',
        TemplateView.as_view(
            template_name='auth/teachers_auth/login/login.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='teachers_login',
    ),

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


    path(
        'auth/teachers_assistants/signup/',
        TemplateView.as_view(
            template_name='auth/teachers_assistants_auth/signup/signup.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='teachers_assistants_signup',
    ),
    path(
        'auth/teachers_assistants/login/',
        TemplateView.as_view(
            template_name='auth/teachers_assistants_auth/login/login.html',
            extra_context={
                'SUPABASE_URL': settings.SUPABASE_URL,
                'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
            },
        ),
        name='teachers_assistants_login',
    ),

    # New: TA auth helper endpoints
    path('assistants/validate-code/', validate_ta_code, name='assistants_validate_code'),
    path('assistants/register/', register_ta, name='assistants_register'),
    path('assistants/resend-confirmation/', resend_ta_confirmation, name='assistants_resend_confirmation'),
    path('assistants/confirm-signup/', confirm_ta_signup, name='assistants_confirm_signup'),

    path('dashboard/assistants/', include('teachers_assistants_dash.urls')),

]

# Serve uploaded media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
from helpers.supabase.supabase_client import get_supabase, get_supabase_service
from .models import Teacher, TeacherCode
from django.contrib.auth import get_user_model
from django.urls import reverse

def ping_supabase(request):
    try:
        supabase = get_supabase()
        res = supabase.table("YOUR_TABLE").select("*").limit(1).execute()
        return JsonResponse({"ok": True, "count": len(res.data), "data": res.data})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

def dashboard(request):
    return render(request, 'teachers_dash/teachers_dash.html')

@csrf_exempt
def register_teacher(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        special_code = data.get('special_code')
        if not special_code:
            return JsonResponse({'ok': False, 'error': 'special_code required'}, status=400)

        code_obj = TeacherCode.objects.filter(special_code=special_code).first()
        if not code_obj:
            return JsonResponse({'ok': False, 'error': 'Invalid special_code'}, status=404)

        email = (data.get('email') or '').strip()
        supabase_user_id = data.get('supabase_user_id')

        supabase_admin = get_supabase_service()
        email_confirmed = False
        email_confirmed_at = None
        confirm_link = None

        if supabase_user_id:
            try:
                admin_user_resp = supabase_admin.auth.admin.get_user_by_id(supabase_user_id)
                user_obj = getattr(admin_user_resp, 'user', None)
                email_in_auth = None
                if isinstance(user_obj, dict):
                    email_confirmed_at = user_obj.get('email_confirmed_at')
                    email_in_auth = user_obj.get('email')
                else:
                    email_confirmed_at = getattr(user_obj, 'email_confirmed_at', None)
                    email_in_auth = getattr(user_obj, 'email', None)
                email_confirmed = bool(email_confirmed_at)

                if not email_confirmed and email_in_auth:
                    try:
                        redirect_to = request.build_absolute_uri(reverse('teachers_signup'))
                        gen = supabase_admin.auth.admin.generate_link(
                            type='signup',
                            email=email_in_auth,
                            options={'redirect_to': redirect_to},
                        )
                        data_obj = getattr(gen, 'data', gen)
                        confirm_link = data_obj.get('action_link') if isinstance(data_obj, dict) else getattr(data_obj, 'action_link', None)
                    except Exception:
                        pass
            except Exception:
                email_confirmed = False
                email_confirmed_at = None

        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if not user:
            base_username = email or (data.get('first_name') or 'teacher').lower()
            username = base_username
            if User.objects.filter(username=username).exists():
                base_username = (email.split('@')[0] if email else 'teacher')
                i = 1
                while User.objects.filter(username=f'{base_username}{i}').exists():
                    i += 1
                username = f'{base_username}{i}'
            user = User(username=username, email=email)
            user.set_unusable_password()
            user.save()

        teacher, created = Teacher.objects.get_or_create(
            email=email,
            defaults={
                'user_id': supabase_user_id,
                'first_name': (data.get('first_name') or '').strip(),
                'last_name': (data.get('last_name') or '').strip(),
                'title': data.get('title'),
                'special_code': special_code,
                'phone': (data.get('phone') or '').strip(),
                'code': code_obj,
                'django_user': user,
                'email_confirmed': email_confirmed,
            }
        )

        if not created:
            teacher.code = code_obj
            teacher.first_name = (data.get('first_name') or teacher.first_name)
            teacher.last_name = (data.get('last_name') or teacher.last_name)
            teacher.title = data.get('title') or teacher.title
            teacher.special_code = special_code or teacher.special_code
            teacher.phone = (data.get('phone') or teacher.phone)
            teacher.user_id = supabase_user_id or teacher.user_id
            teacher.django_user = user
            if email_confirmed_at is not None:
                teacher.email_confirmed = email_confirmed
            teacher.save()

        return JsonResponse({
            'ok': True,
            'created': created,
            'teacher_id': teacher.id,
            'teacher_uid': getattr(teacher, 'user_uid', None),
            'email': email,
            'confirmed': bool(teacher.email_confirmed),
            'email_confirmed_at': email_confirmed_at,
            'confirm_link': confirm_link,
            'redirect_to': '/dashboard/teacher/' if teacher.email_confirmed else None,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def resend_confirmation_email(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        email = (data.get('email') or '').strip()
        if not email:
            return JsonResponse({'ok': False, 'error': 'email required'}, status=400)

        supabase_admin = get_supabase_service()
        redirect_to = request.build_absolute_uri(reverse('teachers_signup'))
        gen = supabase_admin.auth.admin.generate_link(
            type='signup',
            email=email,
            options={'redirect_to': redirect_to},
        )
        data_obj = getattr(gen, 'data', gen)
        if isinstance(data_obj, dict):
            confirm_link = data_obj.get('action_link')
        else:
            confirm_link = getattr(data_obj, 'action_link', None)

        return JsonResponse({'ok': True, 'confirm_link': confirm_link, 'redirect_to': redirect_to})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def confirm_teacher_signup(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        supabase_user_id = data.get('supabase_user_id')
        if not supabase_user_id:
            return JsonResponse({'ok': False, 'error': 'supabase_user_id required'}, status=400)

        supabase_admin = get_supabase_service()
        admin_user_resp = supabase_admin.auth.admin.get_user_by_id(supabase_user_id)
        user_obj = getattr(admin_user_resp, 'user', None)

        email = None
        confirmed_at = None
        if isinstance(user_obj, dict):
            email = user_obj.get('email')
            confirmed_at = user_obj.get('email_confirmed_at')
        else:
            email = getattr(user_obj, 'email', None)
            confirmed_at = getattr(user_obj, 'email_confirmed_at', None)

        confirmed = bool(confirmed_at)

        teacher = Teacher.objects.filter(user_id=supabase_user_id).first()
        if teacher:
            teacher.email_confirmed = confirmed
            teacher.save()

        return JsonResponse({
            'ok': True,
            'confirmed': confirmed,
            'email': email,
            'email_confirmed_at': confirmed_at,
            'redirect_to': '/dashboard/teacher/' if confirmed else None,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
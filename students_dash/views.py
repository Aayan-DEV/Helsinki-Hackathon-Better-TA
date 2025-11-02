from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from .models import Student
from teachers_dash.models import Course, Exercise, ExerciseGroupTime
from teachers_assistants_dash.models import TAExerciseSession, TAExerciseSessionSubmission
from .models import StudentExerciseGroupSelection
from django.utils import timezone

def dashboard(request):
    return render(request, 'students_dash/students_dash.html', {
        'student_name': request.session.get('student_name', ''),
        'student_email': request.session.get('student_email', ''),
        'student_id': request.session.get('student_id', ''),
    })

def exercises_page(request):
    return render(request, 'students_dash/exercises.html', {
        'student_name': request.session.get('student_name', ''),
        'student_email': request.session.get('student_email', ''),
        'student_id': request.session.get('student_id', ''),
    })

def grades_page(request):
    return render(request, 'students_dash/grades.html', {
        'student_name': request.session.get('student_name', ''),
        'student_email': request.session.get('student_email', ''),
        'student_id': request.session.get('student_id', ''),
    })

@csrf_exempt
def api_exercises_full(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)

    student_pk = request.session.get('student_pk')
    if not student_pk:
        return JsonResponse({'ok': False, 'error': 'Not authenticated'}, status=401)

    student = Student.objects.filter(pk=student_pk).first()
    if not student:
        return JsonResponse({'ok': False, 'error': 'Student not found'}, status=404)

    def dt_str(dt):
        return dt.isoformat() if dt else None

    # Courses enrolled
    courses_qs = Course.objects.filter(students=student).select_related('teacher').order_by('title')
    courses = [{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'teacher_email': getattr(c.teacher, 'email', ''),
        'enrolled_count': c.enrolled_count,
        'created_at': dt_str(c.created_at),
    } for c in courses_qs]

    # All exercises in enrolled courses
    exercises_qs = Exercise.objects.filter(course__in=list(courses_qs)).select_related('course').order_by('-created_at')

    # Student sign-ups (group time selections)
    selections = StudentExerciseGroupSelection.objects.filter(student=student)
    selection_map = {s.exercise_id: s.group_time_id for s in selections}

    # Group times per exercise
    group_times_map = {}
    for ex in exercises_qs:
        times = ExerciseGroupTime.objects.filter(exercise=ex).order_by('scheduled_at')
        group_times_map[ex.id] = [{'id': t.id, 'name': t.name, 'scheduled_at': dt_str(t.scheduled_at)} for t in times]

    # Questions per exercise
    questions_map = {}
    from teachers_dash.models import ExerciseQuestion
    for ex in exercises_qs:
        qs = ExerciseQuestion.objects.filter(exercise=ex).order_by('order')
        questions_map[ex.id] = [{'id': q.id, 'text': q.question_text, 'points': q.points, 'order': q.order} for q in qs]

    # Sessions attended by this student (with grades)
    subs_qs = TAExerciseSessionSubmission.objects.filter(
        student_id=student.student_id
    ).select_related('session__course', 'session__exercise', 'session__assistant').order_by('-updated_at', '-created_at')

    sessions_attended = []
    for s in subs_qs:
        sess = s.session
        ex = sess.exercise
        sessions_attended.append({
            'id': s.id,
            'slug': sess.slug,
            'course': {
                'id': sess.course_id,
                'title': sess.course.title if sess.course else '',
            },
            'exercise': {
                'id': ex.id if ex else None,
                'title': ex.title if ex else None,
                'total_points': ex.total_points if ex else None,
            },
            'assistant_name': getattr(sess.assistant, 'name', None),
            'answers': s.answers_json,
            'total_checked_count': s.total_checked_count,
            'score': s.score,
            'group_index': s.group_index,
            'submitted_at': dt_str(s.updated_at),
            'evidence_requested_at': dt_str(getattr(s, 'evidence_requested_at', None)),
            'evidence_received_at': dt_str(getattr(s, 'evidence_received_at', None)),
        })

    # Build exercises payload
    exercises = []
    signed_up_ids = set(selection_map.keys())
    for e in exercises_qs:
        selected_gt_id = selection_map.get(e.id)
        exercises.append({
            'id': e.id,
            'title': e.title,
            'details': e.details,
            'total_points': e.total_points,
            'start_time': dt_str(e.start_time),
            'deadline': dt_str(e.deadline),
            'created_at': dt_str(e.created_at),
            'course': {
                'id': e.course_id,
                'title': e.course.title,
                'description': e.course.description,
            },
            'questions': questions_map.get(e.id, []),
            'group_times': group_times_map.get(e.id, []),
            'selected_group_time_id': selected_gt_id,
        })

    not_signed_up = [ex for ex in exercises if ex['id'] not in signed_up_ids]
    signed_up = []
    if signed_up_ids:
        # Expand signed-up with selected group time details
        gt_qs = ExerciseGroupTime.objects.filter(id__in=list(selection_map.values()))
        gt_map = {gt.id: gt for gt in gt_qs}
        for ex in exercises:
            if ex['id'] in signed_up_ids:
                gt_id = ex['selected_group_time_id']
                gt = gt_map.get(gt_id)
                signed_up.append({
                    'exercise_id': ex['id'],
                    'exercise_title': ex['title'],
                    'course_title': ex['course']['title'],
                    'group_time': {
                        'id': gt_id,
                        'name': getattr(gt, 'name', None),
                        'scheduled_at': dt_str(getattr(gt, 'scheduled_at', None)),
                    }
                })

    stats = {
        'courses_count': len(courses),
        'exercises_count': len(exercises),
        'signed_up_count': len(signed_up),
        'not_signed_up_count': len(not_signed_up),
        'sessions_attended_count': len(sessions_attended),
        'avg_score': (sum([s['score'] for s in sessions_attended if s['score'] is not None]) / max(1, len([s for s in sessions_attended if s['score'] is not None]))) if sessions_attended else None,
    }

    return JsonResponse({
        'ok': True,
        'student': {
            'id': student.pk,
            'name': student.name,
            'email': student.email,
            'student_id': student.student_id,
        },
        'stats': stats,
        'courses': courses,
        'exercises': exercises,
        'signed_up': signed_up,
        'not_signed_up': not_signed_up,
        'sessions_attended': sessions_attended,
    })

@csrf_exempt
def api_evidence_upload(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)

    student_pk = request.session.get('student_pk')
    if not student_pk:
        return JsonResponse({'ok': False, 'error': 'Not authenticated'}, status=401)

    student = Student.objects.filter(pk=student_pk).first()
    if not student:
        return JsonResponse({'ok': False, 'error': 'Student not found'}, status=404)

    # Expect multipart/form-data with submission_id and file field "evidence"
    try:
        submission_id = int((request.POST.get('submission_id') or '0').strip())
    except Exception:
        submission_id = 0
    file_obj = request.FILES.get('evidence')

    if not submission_id or not file_obj:
        return JsonResponse({'ok': False, 'error': 'submission_id and evidence file required'}, status=400)

    sub = TAExerciseSessionSubmission.objects.filter(id=submission_id, student_id=student.student_id).first()
    if not sub:
        return JsonResponse({'ok': False, 'error': 'Submission not found'}, status=404)

    sub.evidence_file = file_obj
    sub.evidence_received_at = timezone.now()
    # Optional: mark state for teacher review
    sub.evidence_decision = ''  # pending review
    sub.save(update_fields=['evidence_file', 'evidence_received_at', 'evidence_decision', 'updated_at'])

    evidence_url = sub.evidence_file.url if sub.evidence_file else None
    return JsonResponse({'ok': True, 'evidence_url': evidence_url})
    
def extras_page(request):
    return render(request, 'students_dash/extras.html', {
        'student_name': request.session.get('student_name', ''),
        'student_email': request.session.get('student_email', ''),
        'student_id': request.session.get('student_id', ''),
    })

@csrf_exempt
def students_logout_api(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    request.session.flush()
    return JsonResponse({'ok': True, 'redirect': reverse('students_login')})

@csrf_exempt
def api_dashboard_summary(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    student_pk = request.session.get('student_pk')
    if not student_pk:
        return JsonResponse({'ok': False, 'error': 'Not authenticated'}, status=401)
    student = Student.objects.filter(pk=student_pk).first()
    if not student:
        return JsonResponse({'ok': False, 'error': 'Student not found'}, status=404)

    courses_qs = Course.objects.filter(students=student).select_related('teacher').order_by('title')
    courses = [{
        'id': c.id,
        'title': c.title,
        'teacher_email': getattr(c.teacher, 'email', ''),
        'enrolled_count': c.enrolled_count,
    } for c in courses_qs]

    exercises_qs = Exercise.objects.filter(course__in=list(courses_qs)).order_by('-created_at')
    submitted_ex_ids = set(TAExerciseSessionSubmission.objects.filter(
        student_id=student.student_id,
        session__exercise__in=exercises_qs
    ).values_list('session__exercise_id', flat=True))
    uncompleted = [{
        'id': e.id,
        'title': e.title,
        'course_id': e.course_id,
        'course_title': e.course.title,
        'deadline': e.deadline.isoformat() if e.deadline else None,
        'start_time': e.start_time.isoformat() if e.start_time else None,
    } for e in exercises_qs if e.id not in submitted_ex_ids]

    selected_ex_ids = set(StudentExerciseGroupSelection.objects.filter(student=student).values_list('exercise_id', flat=True))
    no_time_selected = [{
        'id': e.id,
        'title': e.title,
        'course_id': e.course_id,
        'course_title': e.course.title,
    } for e in exercises_qs if e.id not in selected_ex_ids]

    evidence_reqs_qs = TAExerciseSessionSubmission.objects.filter(
        student_id=student.student_id,
        evidence_requested_at__isnull=False,
        evidence_received_at__isnull=True
    ).select_related('session__course', 'session__exercise').order_by('-evidence_requested_at')
    evidence_requests = [{
        'session_slug': s.session.slug,
        'course_title': s.session.course.title,
        'exercise_title': s.session.exercise.title if s.session.exercise else '',
        'requested_at': s.evidence_requested_at.isoformat() if s.evidence_requested_at else None,
    } for s in evidence_reqs_qs]

    return JsonResponse({
        'ok': True,
        'courses': courses,
        'exercises_uncompleted': uncompleted,
        'exercises_no_time_selected': no_time_selected,
        'evidence_requests': evidence_requests,
    })

@csrf_exempt
def api_exercise_group_times(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST
    exercise_id = int(data.get('exercise_id') or 0)
    student_pk = request.session.get('student_pk')
    if not exercise_id or not student_pk:
        return JsonResponse({'ok': False, 'error': 'exercise_id required and auth'}, status=400)
    student = Student.objects.filter(pk=student_pk).first()
    ex = Exercise.objects.filter(id=exercise_id).first()
    if not ex:
        return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)
    if not Course.objects.filter(id=ex.course_id, students=student).exists():
        return JsonResponse({'ok': False, 'error': 'Not enrolled for this exercise'}, status=403)
    times = ExerciseGroupTime.objects.filter(exercise=ex).order_by('scheduled_at')
    selected = StudentExerciseGroupSelection.objects.filter(student=student, exercise=ex).first()
    return JsonResponse({
        'ok': True,
        'group_times': [{'id': t.id, 'name': t.name, 'scheduled_at': t.scheduled_at.isoformat()} for t in times],
        'selected_group_time_id': selected.group_time_id if selected else None
    })

@csrf_exempt
def api_select_group_time(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST
    exercise_id = int(data.get('exercise_id') or 0)
    group_time_id = int(data.get('group_time_id') or 0)
    student_pk = request.session.get('student_pk')
    if not exercise_id or not group_time_id or not student_pk:
        return JsonResponse({'ok': False, 'error': 'exercise_id, group_time_id required and auth'}, status=400)
    student = Student.objects.filter(pk=student_pk).first()
    ex = Exercise.objects.filter(id=exercise_id).first()
    gt = ExerciseGroupTime.objects.filter(id=group_time_id, exercise_id=exercise_id).first()
    if not ex or not gt:
        return JsonResponse({'ok': False, 'error': 'Exercise or group time not found'}, status=404)
    if not Course.objects.filter(id=ex.course_id, students=student).exists():
        return JsonResponse({'ok': False, 'error': 'Not enrolled for this exercise'}, status=403)
    StudentExerciseGroupSelection.objects.update_or_create(
        student=student,
        exercise=ex,
        defaults={'group_time': gt}
    )
    return JsonResponse({'ok': True, 'selected_group_time_id': gt.id})

def students_login_page(request):
    return render(request, 'auth/students_auth/login/login.html')

@csrf_exempt
def students_login_api(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    identifier = (data.get('identifier') or '').strip()
    password = (data.get('password') or '').strip()
    if not identifier or not password:
        return JsonResponse({'ok': False, 'error': 'Identifier and password required'}, status=400)

    student = Student.objects.filter(email__iexact=identifier).first()
    if not student:
        student = Student.objects.filter(student_id__iexact=identifier).first()

    if not student or not student.check_password(password):
        return JsonResponse({'ok': False, 'error': 'Invalid credentials'}, status=401)

    # Store basic session info
    request.session['student_pk'] = student.pk
    request.session['student_name'] = student.name
    request.session['student_email'] = student.email
    request.session['student_id'] = student.student_id

    return JsonResponse({'ok': True, 'redirect': reverse('students_dashboard_direct')})
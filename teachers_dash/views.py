from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
from helpers.supabase.supabase_client import get_supabase, get_supabase_service
from .models import Teacher, TeacherCode, Course, Exercise, ExerciseQuestion
from django.contrib.auth import get_user_model
from django.urls import reverse
from teachers_assistants_dash.models import TeachingAssistant, CourseAssistant
from .models import ExerciseGroupTime
from django.utils import timezone
from teachers_assistants_dash.models import TAExerciseSessionSubmission

@csrf_exempt
def api_exercise_group_time_list(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        exercise_id = int(data.get('exercise_id') or 0)

        if not user_id or not course_id or not exercise_id:
            return JsonResponse({'ok': False, 'error': 'user_id, course_id, exercise_id required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id, teacher=teacher).first()
        if not course:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        ex = Exercise.objects.filter(id=exercise_id, course=course).first()
        if not ex:
            return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)

        items = [{'id': gt.id, 'name': gt.name, 'scheduled_at': gt.scheduled_at.isoformat()} for gt in ex.group_times.order_by('scheduled_at')]
        return JsonResponse({'ok': True, 'group_times': items})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_exercise_group_time_create(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        exercise_id = int(data.get('exercise_id') or 0)
        name = (data.get('name') or '').strip()
        scheduled_at_str = (data.get('scheduled_at') or '').strip()

        if not user_id or not course_id or not exercise_id or not name or not scheduled_at_str:
            return JsonResponse({'ok': False, 'error': 'user_id, course_id, exercise_id, name, scheduled_at required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id, teacher=teacher).first()
        if not course:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        ex = Exercise.objects.filter(id=exercise_id, course=course).first()
        if not ex:
            return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)

        from datetime import datetime
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except Exception:
            return JsonResponse({'ok': False, 'error': 'Invalid scheduled_at format'}, status=400)

        gt = ExerciseGroupTime.objects.create(exercise=ex, name=name, scheduled_at=scheduled_at)
        return JsonResponse({'ok': True, 'group_time': {'id': gt.id, 'name': gt.name, 'scheduled_at': gt.scheduled_at.isoformat()}})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def ping_supabase(request):
    try:
        supabase = get_supabase()
        res = supabase.table("YOUR_TABLE").select("*").limit(1).execute()
        return JsonResponse({"ok": True, "count": len(res.data), "data": res.data})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

def course_exercises_page(request, course_id):
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return render(request, 'teachers_dash/menu/courses/exercises.html', {
            'course': None,
            'error': 'Course not found'
        })
    return render(request, 'teachers_dash/menu/courses/exercises.html', {
        'course': course
    })

@csrf_exempt
def api_exercise_create(request):
    # Create an exercise for a course; supports single "details" or separate questions
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        title = (data.get('title') or '').strip()
        mode = (data.get('mode') or 'single').strip()  # 'single' or 'multi'
        details = (data.get('details') or '').strip()
        points = data.get('points')
        try:
            points = int(points) if points is not None and str(points).strip() != '' else None
        except Exception:
            points = None
        start_time_str = (data.get('start_time') or '').strip()
        deadline_str = (data.get('deadline') or '').strip()
        questions = data.get('questions') or []

        if not user_id or not course_id or not title:
            return JsonResponse({'ok': False, 'error': 'user_id, course_id, title required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id).first()
        if not course or course.teacher_id != teacher.id:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        # Parse datetimes (expects "YYYY-MM-DDTHH:MM" from <input type="datetime-local">)
        from datetime import datetime
        def parse_dt(s):
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return None

        start_dt = parse_dt(start_time_str)
        deadline_dt = parse_dt(deadline_str)

        exercise = Exercise.objects.create(
            course=course,
            title=title,
            details=details if mode == 'single' else (details or ''),
            total_points=points if (mode == 'single' and points is not None) else 0,
            start_time=start_dt,
            deadline=deadline_dt,
        )

        created_questions = []
        if mode == 'multi' and isinstance(questions, list) and questions:
            total = 0
            for idx, q in enumerate(questions):
                q_text = (q.get('text') or '').strip()
                q_pts_raw = q.get('points')
                try:
                    q_pts = int(q_pts_raw) if q_pts_raw is not None and str(q_pts_raw).strip() != '' else 0
                except Exception:
                    q_pts = 0
                if not q_text:
                    # Skip empty questions
                    continue
                eq = ExerciseQuestion.objects.create(
                    exercise=exercise,
                    question_text=q_text,
                    points=q_pts,
                    order=idx + 1
                )
                created_questions.append({'id': eq.id, 'text': eq.question_text, 'points': eq.points, 'order': eq.order})
                total += q_pts
            exercise.total_points = total
            exercise.save()

        return JsonResponse({
        'ok': True,
        'exercise': {
            'id': exercise.id,
            'title': exercise.title,
            'mode': mode,
            'total_points': exercise.total_points,
            'questions_count': len(created_questions),
        },
        'questions': created_questions,
    })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_exercise_delete(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        exercise_id = int(data.get('exercise_id') or 0)

        if not user_id or not course_id or not exercise_id:
            return JsonResponse({'ok': False, 'error': 'user_id, course_id, exercise_id required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id, teacher=teacher).first()
        if not course:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        exercise = Exercise.objects.filter(id=exercise_id, course=course).first()
        if not exercise:
            return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)

        exercise.delete()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_exercise_list(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        if not user_id or not course_id:
            return JsonResponse({'ok': False, 'error': 'user_id and course_id required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id).first()
        if not course or course.teacher_id != teacher.id:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        def dt_str(dt):
            return dt.isoformat() if dt else None

        ex_qs = Exercise.objects.filter(course=course).order_by('-created_at')
        exercises = [{
            'id': e.id,
            'title': e.title,
            'details': e.details,
            'total_points': e.total_points,
            'start_time': dt_str(e.start_time),
            'deadline': dt_str(e.deadline),
            'questions_count': e.questions.count(),
        } for e in ex_qs]
        return JsonResponse({'ok': True, 'exercises': exercises})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_exercise_get(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        exercise_id = int(data.get('exercise_id') or 0)
        course_id = int(data.get('course_id') or 0)
        user_id = (data.get('user_id') or '').strip()
        assistant_id = int(data.get('assistant_id') or 0)
        assistant_code = (data.get('assistant_code') or '').strip()

        if not exercise_id or not course_id:
            return JsonResponse({'ok': False, 'error': 'exercise_id and course_id required'}, status=400)

        course = Course.objects.filter(id=course_id).first()
        if not course:
            return JsonResponse({'ok': False, 'error': 'Course not found'}, status=404)

        if user_id:
            teacher = Teacher.objects.filter(user_id=user_id).first()
            if not teacher or course.teacher_id != teacher.id:
                return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)
        else:
            ta = None
            if assistant_id:
                ta = TeachingAssistant.objects.filter(id=assistant_id).first()
            if not ta and assistant_code:
                ta = TeachingAssistant.objects.filter(special_code=assistant_code).first()
            if not ta:
                return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)
            if not CourseAssistant.objects.filter(course=course, assistant=ta).exists():
                return JsonResponse({'ok': False, 'error': 'Assistant not assigned to this course'}, status=403)

        ex = Exercise.objects.filter(id=exercise_id, course=course).first()
        if not ex:
            return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)

        qs = ex.questions.order_by('order').values('id', 'question_text', 'points', 'order')
        return JsonResponse({
            'ok': True,
            'exercise': {
                'id': ex.id,
                'title': ex.title,
                'details': ex.details,
                'total_points': ex.total_points,
                'start_time': ex.start_time.isoformat() if ex.start_time else None,
                'deadline': ex.deadline.isoformat() if ex.deadline else None,
            },
            'questions': [{'id': q['id'], 'text': q['question_text'], 'points': q['points'], 'order': q['order']} for q in qs],
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_exercise_update(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        exercise_id = int(data.get('exercise_id') or 0)
        course_id = int(data.get('course_id') or 0)
        user_id = (data.get('user_id') or '').strip()
        assistant_id = int(data.get('assistant_id') or 0)
        assistant_code = (data.get('assistant_code') or '').strip()
        title = (data.get('title') or '').strip()
        mode = (data.get('mode') or 'single').strip()
        details = (data.get('details') or '').strip()
        points_raw = data.get('points')
        try:
            points = int(points_raw) if points_raw is not None and str(points_raw).strip() != '' else None
        except Exception:
            points = None
        start_time_str = (data.get('start_time') or '').strip()
        deadline_str = (data.get('deadline') or '').strip()
        questions = data.get('questions') or []

        if not exercise_id or not course_id:
            return JsonResponse({'ok': False, 'error': 'exercise_id and course_id required'}, status=400)

        course = Course.objects.filter(id=course_id).first()
        if not course:
            return JsonResponse({'ok': False, 'error': 'Course not found'}, status=404)

        if user_id:
            teacher = Teacher.objects.filter(user_id=user_id).first()
            if not teacher or course.teacher_id != teacher.id:
                return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)
        else:
            ta = None
            if assistant_id:
                ta = TeachingAssistant.objects.filter(id=assistant_id).first()
            if not ta and assistant_code:
                ta = TeachingAssistant.objects.filter(special_code=assistant_code).first()
            if not ta:
                return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)
            if not CourseAssistant.objects.filter(course=course, assistant=ta).exists():
                return JsonResponse({'ok': False, 'error': 'Assistant not assigned to this course'}, status=403)

        ex = Exercise.objects.filter(id=exercise_id, course=course).first()
        if not ex:
            return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)

        from datetime import datetime
        def parse_dt(s):
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return None

        ex.title = title or ex.title
        ex.details = details if mode == 'single' else (details or '')
        ex.start_time = parse_dt(start_time_str)
        ex.deadline = parse_dt(deadline_str)

        if mode == 'single':
            ex.questions.all().delete()
            if points is not None:
                ex.total_points = points
        else:
            ex.questions.all().delete()
            total = 0
            for idx, q in enumerate(questions):
                q_text = (q.get('text') or '').strip()
                if not q_text:
                    continue
                q_pts_raw = q.get('points')
                try:
                    q_pts = int(q_pts_raw) if q_pts_raw is not None and str(q_pts_raw).strip() != '' else 0
                except Exception:
                    q_pts = 0
                ExerciseQuestion.objects.create(
                    exercise=ex,
                    question_text=q_text,
                    points=q_pts,
                    order=idx + 1
                )
                total += q_pts
            ex.total_points = total

        ex.save()
        return JsonResponse({'ok': True, 'exercise_id': ex.id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def dashboard(request):
    return render(request, 'teachers_dash/teachers_dash.html')

@csrf_exempt
def api_evidence_list(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST
    user_id = (data.get('user_id') or '').strip()
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'user_id required'}, status=400)

    teacher = Teacher.objects.filter(user_id=user_id).first()
    if not teacher:
        return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

    subs = TAExerciseSessionSubmission.objects.select_related(
        'session__course', 'session__exercise', 'session__assistant'
    ).filter(
        session__course__teacher=teacher,
        evidence_requested_at__isnull=False
    ).order_by('-evidence_requested_at', '-updated_at')

    items = []
    for s in subs:
        sess = s.session
        ex = sess.exercise
        items.append({
            'id': s.id,
            'student_id': s.student_id,
            'student_name': s.student_name,
            'course': {'id': sess.course_id, 'title': sess.course.title},
            'exercise': {
                'id': ex.id if ex else None,
                'title': ex.title if ex else None,
                'total_points': ex.total_points if ex else None,
            },
            'assistant_name': getattr(sess.assistant, 'name', None),
            'group_index': s.group_index,
            'score': s.score,
            'requested_at': s.evidence_requested_at.isoformat() if s.evidence_requested_at else None,
            'received_at': s.evidence_received_at.isoformat() if s.evidence_received_at else None,
            'evidence_url': (s.evidence_file.url if s.evidence_file else None),
            'decision': s.evidence_decision or '',
            'reviewed_at': s.evidence_reviewed_at.isoformat() if s.evidence_reviewed_at else None,
        })
    return JsonResponse({'ok': True, 'items': items})

@csrf_exempt
def api_evidence_decision(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST
    user_id = (data.get('user_id') or '').strip()
    submission_id = int(data.get('submission_id') or 0)
    decision = (data.get('decision') or '').strip().lower()  # 'accept' or 'decline'
    new_score_raw = data.get('new_score', None)
    try:
        new_score = int(new_score_raw) if new_score_raw is not None and str(new_score_raw).strip() != '' else None
    except Exception:
        new_score = None

    if not user_id or not submission_id or decision not in ('accept', 'decline'):
        return JsonResponse({'ok': False, 'error': 'user_id, submission_id, decision required'}, status=400)

    teacher = Teacher.objects.filter(user_id=user_id).first()
    if not teacher:
        return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

    sub = TAExerciseSessionSubmission.objects.select_related('session__course').filter(id=submission_id).first()
    if not sub or sub.session.course.teacher_id != teacher.id:
        return JsonResponse({'ok': False, 'error': 'Unauthorized or submission not found'}, status=403)

    now = timezone.now()
    if decision == 'accept':
        sub.evidence_decision = 'accepted'
        sub.evidence_reviewed_at = now
        sub.save(update_fields=['evidence_decision', 'evidence_reviewed_at', 'updated_at'])
    else:
        # Decline: allow changing the score
        if new_score is None:
            return JsonResponse({'ok': False, 'error': 'new_score required when declining'}, status=400)
        sub.score = new_score
        sub.evidence_decision = 'declined'
        sub.evidence_reviewed_at = now
        sub.save(update_fields=['score', 'evidence_decision', 'evidence_reviewed_at', 'updated_at'])

    return JsonResponse({
        'ok': True,
        'submission_id': sub.id,
        'decision': sub.evidence_decision,
        'score': sub.score,
        'reviewed_at': sub.evidence_reviewed_at.isoformat() if sub.evidence_reviewed_at else None,
    })

def courses_page(request):
    return render(request, 'teachers_dash/menu/courses/courses.html')

def course_detail_page(request, course_id):
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return render(request, 'teachers_dash/menu/courses/course_detail.html', {
            'course': None,
            'error': 'Course not found'
        })
    return render(request, 'teachers_dash/menu/courses/course_detail.html', {
        'course': course
    })

@csrf_exempt
def api_ta_list(request):
    # List TAs assigned to a course
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        if not user_id or not course_id:
            return JsonResponse({'ok': False, 'error': 'user_id and course_id required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id).first()
        if not course or course.teacher_id != teacher.id:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        links = CourseAssistant.objects.filter(course=course).select_related('assistant').order_by('-assigned_at')
        return JsonResponse({'ok': True, 'assistants': [
            {'id': link.assistant.id, 'name': link.assistant.name, 'special_code': link.assistant.special_code}
            for link in links
        ]})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_ta_create(request):
    # Create a global TA and assign to the current course
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        name = (data.get('name') or '').strip()
        special_code = (data.get('special_code') or '').strip()

        if not user_id or not course_id or not name or not special_code:
            return JsonResponse({'ok': False, 'error': 'user_id, course_id, name, special_code required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id).first()
        if not course or course.teacher_id != teacher.id:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        ta = TeachingAssistant.objects.filter(special_code=special_code).first()
        if not ta:
            ta = TeachingAssistant.objects.create(name=name, special_code=special_code)

        # Assign to course (idempotent)
        CourseAssistant.objects.get_or_create(course=course, assistant=ta)

        return JsonResponse({'ok': True, 'assistant': {'id': ta.id, 'name': ta.name, 'special_code': ta.special_code}})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_ta_all(request):
    # Return all global TAs (no auth filter; visible to everyone)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        tas = TeachingAssistant.objects.order_by('-created_at')
        return JsonResponse({'ok': True, 'assistants': [
            {'id': ta.id, 'name': ta.name, 'special_code': ta.special_code}
            for ta in tas
        ]})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_ta_assign(request):
    # Assign an existing TA to a course
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)
        assistant_id = int(data.get('assistant_id') or 0)

        if not user_id or not course_id or not assistant_id:
            return JsonResponse({'ok': False, 'error': 'user_id, course_id, assistant_id required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id).first()
        if not course or course.teacher_id != teacher.id:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        ta = TeachingAssistant.objects.filter(id=assistant_id).first()
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)

        link, created = CourseAssistant.objects.get_or_create(course=course, assistant=ta)
        return JsonResponse({'ok': True, 'assigned': True, 'assistant': {'id': ta.id, 'name': ta.name, 'special_code': ta.special_code}})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def validate_teacher_code(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        special_code = (data.get('special_code') or '').strip()
        if not special_code:
            return JsonResponse({'ok': False, 'error': 'special_code required'}, status=400)
        code_obj = TeacherCode.objects.filter(special_code=special_code).first()
        if not code_obj:
            return JsonResponse({'ok': False, 'error': 'Invalid special_code'}, status=404)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

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

@csrf_exempt
def api_dashboard_counts(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        teacher = Teacher.objects.filter(user_id=user_id).select_related('code').first()
        if not teacher:
            return JsonResponse({
                'ok': True,
                'courses_count': 0,
                'students_count': 0,
                'ta_unique_count': 0,
                'ta_assignments_count': 0,
                'teacher_code': None,
            })

        courses = Course.objects.filter(teacher=teacher)
        courses_count = courses.count()
        students_count = sum(c.enrolled_count for c in courses)

        links = CourseAssistant.objects.filter(course__teacher=teacher)
        ta_assignments_count = links.count()
        ta_unique_count = links.values('assistant_id').distinct().count()

        teacher_code_info = None
        if teacher.code:
            teacher_code_info = {
                'label': teacher.code.label,
                'course_name': teacher.code.course_name,
                'special_code': teacher.code.special_code,
            }

        return JsonResponse({
            'ok': True,
            'courses_count': courses_count,
            'students_count': students_count,
            'ta_unique_count': ta_unique_count,
            'ta_assignments_count': ta_assignments_count,
            'teacher_code': teacher_code_info,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_list_courses(request):
    # Return a list of courses for the teacher (no title/description required)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        user_email = (data.get('user_email') or '').strip().lower()

        if not user_id and not user_email:
            return JsonResponse({'ok': False, 'error': 'user_id or user_email required'}, status=400)

        teacher = None
        if user_id:
            teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher and user_email:
            teacher = Teacher.objects.filter(email__iexact=user_email).first()

        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        courses_qs = Course.objects.filter(teacher=teacher).order_by('-created_at')
        courses = [
            {
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'enrolled_count': c.enrolled_count,
            }
            for c in courses_qs
        ]
        return JsonResponse({'ok': True, 'courses': courses})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_create_course(request):
    # Create a course for the teacher using user_id or user_email
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        user_email = (data.get('user_email') or '').strip().lower()
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()

        if not title or not description:
            return JsonResponse({'ok': False, 'error': 'title and description required'}, status=400)

        teacher = None
        if user_id:
            teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher and user_email:
            teacher = Teacher.objects.filter(email__iexact=user_email).first()

        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.create(teacher=teacher, title=title, description=description)
        return JsonResponse({'ok': True, 'course': {'id': course.id, 'title': course.title}})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_delete_course(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        course_id = int(data.get('course_id') or 0)

        if not user_id or not course_id:
            return JsonResponse({'ok': False, 'error': 'user_id and course_id required'}, status=400)

        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)

        course = Course.objects.filter(id=course_id, teacher=teacher).first()
        if not course:
            return JsonResponse({'ok': False, 'error': 'Course not found or not owned by teacher'}, status=404)

        course.delete()
        return JsonResponse({'ok': True, 'deleted': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_teacher_info(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        user_id = (data.get('user_id') or '').strip()
        if not user_id:
            return JsonResponse({'ok': False, 'error': 'user_id required'}, status=400)
        teacher = Teacher.objects.filter(user_id=user_id).first()
        if not teacher:
            return JsonResponse({'ok': False, 'error': 'Teacher not found'}, status=404)
        full_name = f"{teacher.title} {teacher.first_name} {teacher.last_name}".strip()
        return JsonResponse({
            'ok': True,
            'full_name': full_name,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'title': teacher.title,
            'email': teacher.email,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
# Top-level imports in views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from helpers.supabase.supabase_client import get_supabase_service
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from .models import TeachingAssistant
from .models import CourseAssistant, TAExerciseSession, TAExerciseSessionSubmission
from teachers_dash.models import Course, Exercise, ExerciseQuestion
import random
import string
from students_dash.models import Student
from django.conf import settings

def _generate_slug(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))

def _assistant_from_payload(data):
    assistant_id = int(data.get('assistant_id') or 0)
    assistant_code = (data.get('assistant_code') or '').strip()
    supabase_user_id = (data.get('supabase_user_id') or '').strip()
    email = (data.get('email') or '').strip()

    ta = None
    if assistant_id:
        ta = TeachingAssistant.objects.filter(id=assistant_id).first()
    if not ta and assistant_code:
        ta = TeachingAssistant.objects.filter(special_code=assistant_code).first()
    if not ta and supabase_user_id:
        ta = TeachingAssistant.objects.filter(user_id=supabase_user_id).first()
    if not ta and email:
        ta = TeachingAssistant.objects.filter(email=email).first()
    return ta

@csrf_exempt
def api_assistant_lookup(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        supabase_user_id = (data.get('supabase_user_id') or '').strip()
        email = (data.get('email') or '').strip()

        ta = None
        if supabase_user_id:
            ta = TeachingAssistant.objects.filter(user_id=supabase_user_id).first()
        if not ta and email:
            ta = TeachingAssistant.objects.filter(email=email).first()
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)

        assistant_label = ' '.join(filter(None, [
            getattr(ta, 'title', ''),
            getattr(ta, 'first_name', ''),
            getattr(ta, 'last_name', '')
        ])).strip() or ta.name

        return JsonResponse({
            'ok': True,
            'assistant': {
                'id': ta.id,
                'label': assistant_label,
                'email': getattr(ta, 'email', None),
                'special_code': ta.special_code,
            }
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_list(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)

        qs = TAExerciseSession.objects.filter(
            assistant=ta,
            status__in=['active']
        ).select_related('course', 'exercise').order_by('-started_at', '-created_at')

        payload = []
        for s in qs:
            title = s.title or (s.exercise.title if s.exercise else 'Session')
            payload.append({
                'id': s.id,
                'slug': s.slug,
                'title': title,
                'course_id': s.course_id,
                'course_title': s.course.title if s.course else '',
                'exercise_id': s.exercise_id,
                'exercise_title': s.exercise.title if s.exercise else None,
                'started_at': s.started_at.isoformat() if s.started_at else None,
                'time_limit_minutes': s.time_limit_minutes,
                'public_url': request.build_absolute_uri(reverse('ta_session_form', args=[s.slug])),
            })

        return JsonResponse({'ok': True, 'sessions': payload})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_list_closed(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)

        qs = TAExerciseSession.objects.filter(
            assistant=ta,
            status__in=['closed']
        ).select_related('course', 'exercise').order_by('-ended_at', '-started_at', '-created_at')

        payload = []
        for s in qs:
            title = s.title or (s.exercise.title if s.exercise else 'Session')
            ex = s.exercise
            payload.append({
                'id': s.id,
                'slug': s.slug,
                'title': title,
                'course_id': s.course_id,
                'course_title': s.course.title if s.course else '',
                'exercise': {
                    'id': ex.id if ex else None,
                    'title': ex.title if ex else None,
                    'details': ex.details if ex else None,
                    'total_points': ex.total_points if ex else None,
                },
                'started_at': s.started_at.isoformat() if s.started_at else None,
                'ended_at': s.ended_at.isoformat() if s.ended_at else None,
                'time_limit_minutes': s.time_limit_minutes,
            })
        return JsonResponse({'ok': True, 'sessions': payload})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_end_delete(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        slug = (data.get('slug') or '').strip()
        session_id = int(data.get('session_id') or 0)
        if not ta or (not slug and not session_id):
            return JsonResponse({'ok': False, 'error': 'Assistant and slug/session_id required'}, status=400)

        sess = None
        if slug:
            sess = TAExerciseSession.objects.filter(slug=slug, assistant=ta).select_related('exercise').first()
        if not sess and session_id:
            sess = TAExerciseSession.objects.filter(id=session_id, assistant=ta).select_related('exercise').first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)

        # Mark exercise done by setting its deadline to now; this removes it from 'current' and 'ending soon'
        now = timezone.now()
        if sess.exercise:
            ex = sess.exercise
            # If deadline is null or in the future, close it to now
            if (ex.deadline is None) or (ex.deadline and ex.deadline > now):
                ex.deadline = now
                # Ensure start_time is set if missing to avoid odd ranges
                if ex.start_time is None:
                    ex.start_time = now
                ex.save()

        # Close the session, then delete
        sess.ended_at = now
        sess.status = 'closed'
        sess.save()
        sess.delete()

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_assistant_exercises(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)
        links = CourseAssistant.objects.filter(assistant=ta).select_related('course__teacher')
        payload = []
        for link in links:
            course = link.course
            ex_qs = Exercise.objects.filter(course=course).order_by('-created_at')
            payload.append({
                'course': {
                    'id': course.id,
                    'title': course.title,
                    'teacher': {
                        'id': course.teacher.id,
                        'title': getattr(course.teacher, 'title', ''),
                        'first_name': getattr(course.teacher, 'first_name', ''),
                        'last_name': getattr(course.teacher, 'last_name', ''),
                        'email': getattr(course.teacher, 'email', ''),
                    },
                },
                'exercises': [{
                    'id': e.id,
                    'title': e.title,
                    'details': e.details,
                    'total_points': e.total_points,
                    'start_time': e.start_time.isoformat() if e.start_time else None,
                    'deadline': e.deadline.isoformat() if e.deadline else None,
                    'questions_count': e.questions.count(),
                } for e in ex_qs]
            })
        return JsonResponse({'ok': True, 'courses': payload})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def _make_structure_from_counts(q_count, subparts_same_count=None):
    def q_label(i): return f"Q{i}"
    def sub_label(idx):
        # a..z, then a1..z1, a2..z2, ...
        base = string.ascii_lowercase
        if idx < 26:
            return base[idx]
        times = (idx // 26)
        rem = idx % 26
        return f"{base[rem]}{times}"
    questions = []
    for i in range(1, q_count + 1):
        node = {'label': q_label(i)}
        if isinstance(subparts_same_count, int) and subparts_same_count > 0:
            node['children'] = [{'label': sub_label(s)} for s in range(subparts_same_count)]
        questions.append(node)
    return {'questions': questions}

def _flatten_paths(struct):
    paths = []
    def walk(node, prefix=None):
        label = node.get('label')
        current = label if not prefix else f"{prefix}.{label}"
        children = node.get('children') or []
        if children:
            for ch in children:
                walk(ch, current)
        else:
            paths.append(current)
    for q in (struct.get('questions') or []):
        walk(q, None)
    return paths

@csrf_exempt
def api_session_create(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        course_id = int(data.get('course_id') or 0)
        exercise_id = int(data.get('exercise_id') or 0)
        time_limit_minutes = int(data.get('time_limit_minutes') or 0)
        mode = (data.get('mode') or '').strip()  # 'existing', 'count_only', 'uniform_subparts', 'custom_structure'
        subparts_count = int(data.get('subparts_count') or 0)
        q_count_override = int(data.get('question_count') or 0)
        structure = data.get('structure') or None  # for custom_structure

        if not ta or not course_id:
            return JsonResponse({'ok': False, 'error': 'Assistant and course_id required'}, status=400)
        course = Course.objects.filter(id=course_id).first()
        if not course or not CourseAssistant.objects.filter(course=course, assistant=ta).exists():
            return JsonResponse({'ok': False, 'error': 'Unauthorized or course not found'}, status=403)

        exercise = None
        q_count = 0
        struct_json = {}
        title = ''
        if exercise_id:
            exercise = Exercise.objects.filter(id=exercise_id, course=course).first()
            if not exercise:
                return JsonResponse({'ok': False, 'error': 'Exercise not found'}, status=404)
            title = exercise.title

        if mode == 'existing':
            if not exercise:
                return JsonResponse({'ok': False, 'error': 'No exercise selected for existing mode'}, status=400)
            qs = ExerciseQuestion.objects.filter(exercise=exercise).order_by('order')
            q_count = qs.count()
            struct_json = _make_structure_from_counts(q_count, None)
        elif mode == 'count_only':
            if q_count_override <= 0:
                return JsonResponse({'ok': False, 'error': 'question_count must be > 0'}, status=400)
            struct_json = _make_structure_from_counts(q_count_override, None)
        elif mode == 'uniform_subparts':
            if q_count_override <= 0 or subparts_count <= 0:
                return JsonResponse({'ok': False, 'error': 'question_count and subparts_count must be > 0'}, status=400)
            struct_json = _make_structure_from_counts(q_count_override, subparts_count)
        elif mode == 'custom_structure':
            if not isinstance(structure, dict) or not structure.get('questions'):
                return JsonResponse({'ok': False, 'error': 'structure with questions required'}, status=400)
            struct_json = structure
        else:
            return JsonResponse({'ok': False, 'error': 'Invalid mode'}, status=400)

        slug = _generate_slug(10)
        sess = TAExerciseSession.objects.create(
            slug=slug,
            assistant=ta,
            course=course,
            exercise=exercise,
            title=title,
            time_limit_minutes=max(0, time_limit_minutes),
            structure_json=struct_json,
            status='active',
            started_at=timezone.now(),
        )
        public_url = request.build_absolute_uri(reverse('ta_session_form', args=[sess.slug]))
        return JsonResponse({'ok': True, 'session': {
            'id': sess.id,
            'slug': sess.slug,
            'title': title or 'Session',
            'time_limit_minutes': sess.time_limit_minutes,
            'structure': struct_json,
            'public_url': public_url,
        }})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_get(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        slug = (data.get('slug') or '').strip()
        if not slug:
            return JsonResponse({'ok': False, 'error': 'slug required'}, status=400)
        sess = TAExerciseSession.objects.filter(slug=slug).select_related('assistant', 'course', 'exercise').first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)
        paths = _flatten_paths(sess.structure_json or {})
        public_url = request.build_absolute_uri(reverse('ta_session_form', args=[sess.slug]))
        return JsonResponse({'ok': True, 'session': {
            'id': sess.id,
            'slug': sess.slug,
            'title': sess.title or 'Session',
            'status': sess.status,
            'time_limit_minutes': sess.time_limit_minutes,
            'structure': sess.structure_json or {},
            'checkable_paths': paths,
            'public_url': public_url,
        }})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_update_structure(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        slug = (data.get('slug') or '').strip()
        structure = data.get('structure') or {}
        if not slug or not isinstance(structure, dict):
            return JsonResponse({'ok': False, 'error': 'slug and structure required'}, status=400)
        sess = TAExerciseSession.objects.filter(slug=slug).first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)
        sess.structure_json = structure
        sess.save(update_fields=['structure_json', 'updated_at'] if hasattr(sess, 'updated_at') else ['structure_json'])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_submissions_list(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        slug = (data.get('slug') or '').strip()
        if not slug:
            return JsonResponse({'ok': False, 'error': 'slug required'}, status=400)
        sess = TAExerciseSession.objects.filter(slug=slug).first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)
        subs = TAExerciseSessionSubmission.objects.filter(session=sess).order_by('-updated_at', '-created_at')
        items = []
        for s in subs:
            ev_url = None
            try:
                if s.evidence_file and hasattr(s.evidence_file, 'url') and s.evidence_file.url:
                    ev_url = request.build_absolute_uri(s.evidence_file.url)
            except Exception:
                ev_url = None
            items.append({
                'id': s.id,
                'student_id': s.student_id,
                'student_name': s.student_name,
                'answers': s.answers_json,
                'total_checked_count': s.total_checked_count,
                'submitted_at': s.updated_at.isoformat(),
                'score': s.score if hasattr(s, 'score') else None,
                'group_index': s.group_index if hasattr(s, 'group_index') else None,
                'evidence_requested_at': s.evidence_requested_at.isoformat() if getattr(s, 'evidence_requested_at', None) else None,
                'evidence_received_at': s.evidence_received_at.isoformat() if getattr(s, 'evidence_received_at', None) else None,
                'evidence_url': ev_url,
                'evidence_decision': s.evidence_decision or '',
                'evidence_reviewed_at': s.evidence_reviewed_at.isoformat() if getattr(s, 'evidence_reviewed_at', None) else None,
            })
        return JsonResponse({'ok': True, 'submissions': items})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_submission_evidence_decision(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        submission_id = int(data.get('submission_id') or 0)
        decision = (data.get('decision') or '').strip().lower()
        new_score = data.get('new_score', None)

        if not ta or not submission_id or decision not in ('accept', 'decline'):
            return JsonResponse({'ok': False, 'error': 'Assistant, submission_id and decision required'}, status=400)

        sub = TAExerciseSessionSubmission.objects.filter(id=submission_id).select_related('session').first()
        if not sub:
            return JsonResponse({'ok': False, 'error': 'Submission not found'}, status=404)

        if not sub.session or sub.session.assistant_id != ta.id:
            return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)

        if not sub.evidence_requested_at:
            return JsonResponse({'ok': False, 'error': 'Evidence not requested'}, status=400)
        if not sub.evidence_received_at or not sub.evidence_file:
            return JsonResponse({'ok': False, 'error': 'Evidence not received'}, status=400)

        now = timezone.now()
        updates = ['evidence_decision', 'evidence_reviewed_at', 'updated_at']
        if decision == 'accept':
            sub.evidence_decision = 'accepted'
            sub.evidence_reviewed_at = now
        else:
            if new_score is None or str(new_score).strip() == '':
                return JsonResponse({'ok': False, 'error': 'new_score required for decline'}, status=400)
            try:
                sub.score = int(new_score)
            except Exception:
                return JsonResponse({'ok': False, 'error': 'new_score must be an integer'}, status=400)
            updates.append('score')
            sub.evidence_decision = 'declined'
            sub.evidence_reviewed_at = now

        sub.save(update_fields=updates)
        return JsonResponse({
            'ok': True,
            'submission_id': sub.id,
            'decision': sub.evidence_decision,
            'score': sub.score,
            'reviewed_at': sub.evidence_reviewed_at.isoformat() if sub.evidence_reviewed_at else None,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_submission_request_evidence(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        slug = (data.get('slug') or '').strip()
        student_id = (data.get('student_id') or '').strip()
        if not ta or not slug or not student_id:
            return JsonResponse({'ok': False, 'error': 'Assistant, slug, and student_id required'}, status=400)

        sess = TAExerciseSession.objects.filter(slug=slug, assistant=ta).first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)

        sub = TAExerciseSessionSubmission.objects.filter(session=sess, student_id__iexact=student_id).first()
        if not sub:
            return JsonResponse({'ok': False, 'error': 'Submission not found'}, status=404)

        now = timezone.now()
        sub.evidence_requested_at = now
        sub.save(update_fields=['evidence_requested_at', 'updated_at'])
        return JsonResponse({'ok': True, 'requested_at': now.isoformat(), 'student_id': student_id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_grade_close(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        ta = _assistant_from_payload(data)
        slug = (data.get('slug') or '').strip()
        graded = data.get('graded') or []
        if not ta or not slug:
            return JsonResponse({'ok': False, 'error': 'Assistant and slug required'}, status=400)

        sess = TAExerciseSession.objects.filter(slug=slug, assistant=ta).select_related('exercise').first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)

        updated = 0
        for g in graded:
            sid = (g.get('student_id') or '').strip()
            if not sid:
                continue
            score = g.get('score', None)
            group_index = g.get('group_index', None)

            sub = TAExerciseSessionSubmission.objects.filter(session=sess, student_id__iexact=sid).first()
            if not sub:
                continue
            # Persist grading fields
            sub.score = int(score) if (score is not None and str(score).strip() != '') else None
            sub.group_index = int(group_index) if (group_index is not None and str(group_index).strip() != '') else None
            sub.save(update_fields=['score', 'group_index', 'updated_at'])
            updated += 1

        # Mark exercise as completed (set deadline to now) but do not delete session
        now = timezone.now()
        if sess.exercise:
            ex = sess.exercise
            if (ex.deadline is None) or (ex.deadline and ex.deadline > now):
                ex.deadline = now
                if ex.start_time is None:
                    ex.start_time = now
                ex.save()

        # Close session
        sess.ended_at = now
        sess.status = 'closed'
        sess.save(update_fields=['ended_at', 'status'])

        return JsonResponse({'ok': True, 'updated_count': updated, 'session': {'slug': sess.slug, 'status': sess.status}})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_metrics(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        slug = (data.get('slug') or '').strip()
        if not slug:
            return JsonResponse({'ok': False, 'error': 'slug required'}, status=400)
        sess = TAExerciseSession.objects.filter(slug=slug).first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found'}, status=404)
        total_checkable = len(_flatten_paths(sess.structure_json or {}))
        subs = TAExerciseSessionSubmission.objects.filter(session=sess)
        total_submissions = subs.count()
        total_checks = sum(s.total_checked_count for s in subs)
        percent = 0.0
        if total_submissions > 0 and total_checkable > 0:
            percent = round((total_checks / (total_submissions * total_checkable)) * 100.0, 1)
        return JsonResponse({'ok': True, 'metrics': {
            'total_submissions': total_submissions,
            'total_checkable': total_checkable,
            'total_checks': total_checks,
            'percent_complete_avg': percent,
        }})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def session_form_page(request, slug):
    return render(
            request,
            'teachers_assistants_dash/menu/exercise_management/excercise_question_form.html',
            { 'slug': slug }
        )
@csrf_exempt
def api_session_get_public(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        slug = (data.get('slug') or '').strip()
        if not slug:
            return JsonResponse({'ok': False, 'error': 'slug required'}, status=400)
        sess = TAExerciseSession.objects.filter(slug=slug, status__in=['active']).first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found or not active'}, status=404)
        paths = _flatten_paths(sess.structure_json or {})
        return JsonResponse({'ok': True, 'session': {
            'title': sess.title or 'Session',
            'slug': sess.slug,
            'time_limit_minutes': sess.time_limit_minutes,
            'structure': sess.structure_json or {},
            'checkable_paths': paths,
        }})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_session_submit_public(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        slug = (data.get('slug') or '').strip()
        student_id = (data.get('student_id') or '').strip()
        student_name = (data.get('student_name') or '').strip()
        answers = data.get('answers') or []

        if not slug or not student_id or not student_name or not isinstance(answers, list):
            return JsonResponse({'ok': False, 'error': 'slug, student_id, student_name, answers required'}, status=400)

        # Only allow students present in the database to submit
        student = Student.objects.filter(student_id__iexact=student_id).first()
        if not student:
            return JsonResponse({'ok': False, 'error': 'Invalid student_id'}, status=404)

        sess = TAExerciseSession.objects.filter(slug=slug, status__in=['active']).first()
        if not sess:
            return JsonResponse({'ok': False, 'error': 'Session not found or not active'}, status=404)

        sub, _ = TAExerciseSessionSubmission.objects.update_or_create(
            session=sess,
            student_id=student.student_id,  # use canonical ID
            defaults={
                'student_name': student.name,  # use canonical name from DB
                'answers_json': answers,
                'total_checked_count': len(answers),
            }
        )
        return JsonResponse({'ok': True, 'submission_id': sub.id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_assistant_dashboard_counts(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        assistant_id = int(data.get('assistant_id') or 0)
        assistant_code = (data.get('assistant_code') or '').strip()
        supabase_user_id = (data.get('supabase_user_id') or '').strip()
        email = (data.get('email') or '').strip()

        ta = None
        if assistant_id:
            ta = TeachingAssistant.objects.filter(id=assistant_id).first()
        if not ta and assistant_code:
            ta = TeachingAssistant.objects.filter(special_code=assistant_code).first()
        if not ta and supabase_user_id:
            ta = TeachingAssistant.objects.filter(user_id=supabase_user_id).first()
        if not ta and email:
            ta = TeachingAssistant.objects.filter(email=email).first()
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)

        links = CourseAssistant.objects.filter(assistant=ta).select_related('course__teacher').order_by('-assigned_at')
        courses = [link.course for link in links]
        courses_count = len(courses)
        students_total = sum((c.enrolled_count or 0) for c in courses)

        # Unique teachers the assistant reports to
        teachers_map = {}
        for c in courses:
            t = c.teacher
            teachers_map[t.id] = {
                'id': t.id,
                'title': t.title,
                'first_name': t.first_name,
                'last_name': t.last_name,
                'email': t.email,
            }
        teachers = list(teachers_map.values())

        now = timezone.now()
        most_recent = Exercise.objects.filter(course__in=courses).order_by('-created_at').first()
        current_task = Exercise.objects.filter(
            course__in=courses,
            start_time__lte=now
        ).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=now)
        ).order_by('-start_time').first()
        ending_soon = Exercise.objects.filter(
            course__in=courses,
            deadline__gt=now
        ).order_by('deadline').first()

        def ex_payload(e):
            if not e:
                return None
            return {
                'id': e.id,
                'title': e.title,
                'course_id': e.course_id,
                'course_title': e.course.title,
                'start_time': e.start_time.isoformat() if e.start_time else None,
                'deadline': e.deadline.isoformat() if e.deadline else None,
            }

        # Defensive label if TA profile fields are missing
        assistant_label = ' '.join(filter(None, [
            getattr(ta, 'title', ''),
            getattr(ta, 'first_name', ''),
            getattr(ta, 'last_name', '')
        ])).strip() or ta.name

        return JsonResponse({
            'ok': True,
            'assistant': {
                'id': ta.id,
                'label': assistant_label,
                'email': getattr(ta, 'email', None),
                'special_code': ta.special_code,
            },
            'courses_count': courses_count,
            'students_total': students_total,
            'teachers': teachers,
            'most_recent_exercise': ex_payload(most_recent),
            'current_task': ex_payload(current_task),
            'ending_soon_task': ex_payload(ending_soon),
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_assistant_courses_assigned(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        assistant_id = int(data.get('assistant_id') or 0)
        assistant_code = (data.get('assistant_code') or '').strip()
        supabase_user_id = (data.get('supabase_user_id') or '').strip()
        email = (data.get('email') or '').strip()

        ta = None
        if assistant_id:
            ta = TeachingAssistant.objects.filter(id=assistant_id).first()
        if not ta and assistant_code:
            ta = TeachingAssistant.objects.filter(special_code=assistant_code).first()
        if not ta and supabase_user_id:
            ta = TeachingAssistant.objects.filter(user_id=supabase_user_id).first()
        if not ta and email:
            ta = TeachingAssistant.objects.filter(email=email).first()
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Assistant not found'}, status=404)

        links = CourseAssistant.objects.filter(assistant=ta).select_related('course__teacher').order_by('course__title')
        courses = [link.course for link in links]

        def ex_payload(e):
            return {
                'id': e.id,
                'title': e.title,
                'total_points': e.total_points,
                'start_time': e.start_time.isoformat() if e.start_time else None,
                'deadline': e.deadline.isoformat() if e.deadline else None,
                'questions_count': e.questions.count(),
            }

        def course_payload(c):
            exercises = Exercise.objects.filter(course=c).order_by('-created_at')
            return {
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'enrolled_count': c.enrolled_count,
                'created_at': c.created_at.isoformat() if c.created_at else None,
                'teacher': {
                    'id': c.teacher.id,
                    'title': c.teacher.title,
                    'first_name': c.teacher.first_name,
                    'last_name': c.teacher.last_name,
                    'email': c.teacher.email,
                },
                'exercises': [ex_payload(e) for e in exercises],
            }

        return JsonResponse({'ok': True, 'courses': [course_payload(c) for c in courses]})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def courses_assigned_page(request):
    return render(
        request,
        'teachers_assistants_dash/menu/courses_assigned/courses_assigned.html',
        {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
        },
    )

def exercise_management_page(request):
    return render(
        request,
        'teachers_assistants_dash/menu/exercise_management/exercise_management.html',
        {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
        },
    )

def exercise_checkup_page(request):
    return render(
        request,
        'teachers_assistants_dash/menu/exercise_checkup/exercise_checkup.html',
        {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
        },
    )

def dashboard(request):
    return render(
        request,
        'teachers_assistants_dash/teachers_assistants_dash.html',
        {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
        },
    )

@csrf_exempt
def validate_ta_code(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        special_code = (data.get('special_code') or '').strip()
        if not special_code:
            return JsonResponse({'ok': False, 'error': 'special_code required'}, status=400)
        ta = TeachingAssistant.objects.filter(special_code=special_code).first()
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Invalid special_code'}, status=404)
        # Tell client if code is already claimed by a signed-up assistant
        return JsonResponse({'ok': True, 'claimed': bool(ta.user_id)})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def register_ta(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        special_code = (data.get('special_code') or '').strip()
        email = (data.get('email') or '').strip()
        supabase_user_id = (data.get('supabase_user_id') or '').strip()

        if not special_code:
            return JsonResponse({'ok': False, 'error': 'special_code required'}, status=400)
        ta = TeachingAssistant.objects.filter(special_code=special_code).first()
        if not ta:
            return JsonResponse({'ok': False, 'error': 'Invalid special_code'}, status=404)

        # Prevent claiming a code already assigned to another user
        if ta.user_id and (not supabase_user_id or ta.user_id != supabase_user_id):
            return JsonResponse({'ok': False, 'error': 'This code is already assigned to someone else.'}, status=409)

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
                    redirect_to = request.build_absolute_uri(reverse('teachers_assistants_signup'))
                    gen = supabase_admin.auth.admin.generate_link(
                        type='signup',
                        email=email_in_auth,
                        options={'redirect_to': redirect_to},
                    )
                    data_obj = getattr(gen, 'data', gen)
                    confirm_link = data_obj.get('action_link') if isinstance(data_obj, dict) else getattr(data_obj, 'action_link', None)
            except Exception:
                email_confirmed = False
                email_confirmed_at = None

        # Create a Django user shell (optional, mirrors Teacher flow)
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if not user:
            base_username = email or (data.get('first_name') or 'assistant').lower()
            username = base_username
            if User.objects.filter(username=username).exists():
                base_username = (email.split('@')[0] if email else 'assistant')
                i = 1
                while User.objects.filter(username=f'{base_username}{i}').exists():
                    i += 1
                username = f'{base_username}{i}'
            user = User(username=username, email=email)
            user.set_unusable_password()
            user.save()

        # Update TA record with signup details
        ta.first_name = (data.get('first_name') or ta.first_name or '').strip()
        ta.last_name = (data.get('last_name') or ta.last_name or '').strip()
        ta.title = (data.get('title') or ta.title or '').strip()
        ta.email = email or ta.email
        ta.user_id = supabase_user_id or ta.user_id
        ta.name = f"{ta.first_name} {ta.last_name}".strip() or ta.name
        if email_confirmed_at is not None:
            ta.email_confirmed = email_confirmed
        ta.save()

        return JsonResponse({
            'ok': True,
            'assistant_id': ta.id,
            'email': ta.email,
            'confirmed': bool(ta.email_confirmed),
            'email_confirmed_at': email_confirmed_at,
            'confirm_link': confirm_link,
            'redirect_to': '/dashboard/assistants/' if ta.email_confirmed else None,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def resend_ta_confirmation(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        email = (data.get('email') or '').strip()
        if not email:
            return JsonResponse({'ok': False, 'error': 'email required'}, status=400)

        supabase_admin = get_supabase_service()
        redirect_to = request.build_absolute_uri(reverse('teachers_assistants_signup'))
        gen = supabase_admin.auth.admin.generate_link(
            type='signup',
            email=email,
            options={'redirect_to': redirect_to},
        )
        data_obj = getattr(gen, 'data', gen)
        confirm_link = data_obj.get('action_link') if isinstance(data_obj, dict) else getattr(data_obj, 'action_link', None)

        return JsonResponse({'ok': True, 'confirm_link': confirm_link, 'redirect_to': redirect_to})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def confirm_ta_signup(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        supabase_user_id = (data.get('supabase_user_id') or '').strip()
        if not supabase_user_id:
            return JsonResponse({'ok': False, 'error': 'supabase_user_id required'}, status=400)

        supabase_admin = get_supabase_service()
        admin_user_resp = supabase_admin.auth.admin.get_user_by_id(supabase_user_id)
        user_obj = getattr(admin_user_resp, 'user', None)

        email_confirmed_at = None
        email = None
        if isinstance(user_obj, dict):
            email_confirmed_at = user_obj.get('email_confirmed_at')
            email = user_obj.get('email')
        else:
            email_confirmed_at = getattr(user_obj, 'email_confirmed_at', None)
            email = getattr(user_obj, 'email', None)

        confirmed = bool(email_confirmed_at)

        ta = None
        if confirmed:
            ta = TeachingAssistant.objects.filter(user_id=supabase_user_id).first()
            if not ta and email:
                ta = TeachingAssistant.objects.filter(email=email).first()
            if ta:
                ta.email_confirmed = True
                ta.save()

        return JsonResponse({'ok': True, 'confirmed': confirmed, 'redirect_to': '/dashboard/assistants/' if confirmed else None})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
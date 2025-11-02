from django.urls import path
from .views import dashboard, api_assistant_dashboard_counts, courses_assigned_page, exercise_management_page, exercise_checkup_page, api_assistant_courses_assigned
from .views import (
    api_assistant_exercises,
    api_session_create,
    api_session_get,
    api_session_update_structure,
    api_session_submissions_list,
    api_session_metrics,
    session_form_page,
    api_session_get_public,
    api_session_submit_public,
    api_assistant_lookup,
    api_session_list,
    api_session_end_delete,
    api_session_grade_close,
    api_session_list_closed,
    api_submission_request_evidence,
    api_submission_evidence_decision,
)

urlpatterns = [
    path('', dashboard, name='ta_dashboard'),
    path('api/assistant/lookup/', api_assistant_lookup, name='ta_api_assistant_lookup'),
    path('api/dashboard/counts/', api_assistant_dashboard_counts, name='ta_api_dashboard_counts'),
    path('api/courses-assigned/', api_assistant_courses_assigned, name='ta_api_courses_assigned'),
    path('menu/courses-assigned/', courses_assigned_page, name='ta_courses_assigned'),
    path('menu/exercise-management/', exercise_management_page, name='ta_exercise_management'),
    path('menu/exercise-checkup/', exercise_checkup_page, name='ta_exercise_checkup'),
    path('api/exercises/', api_assistant_exercises, name='ta_api_exercises'),
    path('api/session/create/', api_session_create, name='ta_api_session_create'),
    path('api/session/get/', api_session_get, name='ta_api_session_get'),
    path('api/session/update-structure/', api_session_update_structure, name='ta_api_session_update_structure'),
    path('api/session/submissions/', api_session_submissions_list, name='ta_api_session_submissions'),
    path('api/session/metrics/', api_session_metrics, name='ta_api_session_metrics'),
    path('session/<slug:slug>/form/', session_form_page, name='ta_session_form'),
    path('api/session/public/get/', api_session_get_public, name='ta_api_session_get_public'),
    path('api/session/public/submit/', api_session_submit_public, name='ta_api_session_submit_public'),

    # New session listing & end/delete
    path('api/session/list/', api_session_list, name='ta_api_session_list'),
    path('api/session/list-closed/', api_session_list_closed, name='ta_api_session_list_closed'),
    path('api/session/end-delete/', api_session_end_delete, name='ta_api_session_end_delete'),
     path('api/session/grade-close/', api_session_grade_close, name='ta_api_session_grade_close'),
    path('api/submission/request-evidence/', api_submission_request_evidence, name='ta_api_submission_request_evidence'),
    path('api/submission/evidence-decision/', api_submission_evidence_decision, name='ta_api_submission_evidence_decision'),
]
from django.urls import path
from .views import (
    ping_supabase,
    dashboard,
    courses_page,
    register_teacher,
    resend_confirmation_email,
    confirm_teacher_signup,
    validate_teacher_code,
    api_dashboard_counts,
    api_list_courses,
    api_create_course,
    api_teacher_info,
    course_detail_page,
    api_ta_list,
    api_ta_create,
    api_ta_all,
    api_ta_assign,
    api_delete_course,
    course_exercises_page,
    api_exercise_create,
    api_exercise_list,
    api_exercise_get,
    api_exercise_update,
    api_exercise_delete,
    api_exercise_group_time_list,
    api_exercise_group_time_create,
    api_evidence_list,
    api_evidence_decision,
)

urlpatterns = [
    # Dashboard and menu
    path('', dashboard, name='teachers_dashboard_root'),
    path('dashboard/', dashboard, name='teachers_dashboard'),
    path('menu/courses/', courses_page, name='teachers_courses'),
    path('menu/courses/<int:course_id>/', course_detail_page, name='teachers_course_detail'),

    # Signup/confirmation helpers
    path('register/', register_teacher, name='teachers_register'),
    path('resend-confirmation/', resend_confirmation_email, name='teachers_resend_confirmation'),
    path('confirm-signup/', confirm_teacher_signup, name='teachers_confirm_signup'),
    path('validate-code/', validate_teacher_code, name='teachers_validate_code'),

    # APIs
    path('api/teacher/info/', api_teacher_info, name='teachers_api_teacher_info'),
    path('api/dashboard/counts/', api_dashboard_counts, name='teachers_api_dashboard_counts'),
    path('api/courses/list/', api_list_courses, name='teachers_api_list_courses'),
    path('api/courses/create/', api_create_course, name='teachers_api_create_course'),

    # Teaching assistants APIs for course detail
    path('api/courses/tas/list/', api_ta_list, name='teachers_api_ta_list'),
    path('api/courses/tas/create/', api_ta_create, name='teachers_api_ta_create'),
    path('api/courses/tas/all/', api_ta_all, name='teachers_api_ta_all'),
    path('api/courses/tas/assign/', api_ta_assign, name='teachers_api_ta_assign'),
    path('api/courses/delete/', api_delete_course, name='teachers_api_delete_course'),

    path('menu/courses/<int:course_id>/exercises/', course_exercises_page, name='teachers_course_exercises'),
    path('api/courses/exercises/create/', api_exercise_create, name='teachers_api_exercise_create'),
    path('api/courses/exercises/list/', api_exercise_list, name='teachers_api_exercise_list'),
    path('api/courses/exercises/get/', api_exercise_get, name='teachers_api_exercise_get'),
    path('api/courses/exercises/update/', api_exercise_update, name='teachers_api_exercise_update'),
    path('api/courses/exercises/delete/', api_exercise_delete, name='teachers_api_exercise_delete'),
    path('api/courses/exercises/group-times/list/', api_exercise_group_time_list, name='teachers_api_exercise_group_time_list'),
    path('api/courses/exercises/group-times/create/', api_exercise_group_time_create, name='teachers_api_exercise_group_time_create'),
    # New: evidence review APIs
    path('api/evidence/list/', api_evidence_list, name='teachers_api_evidence_list'),
    path('api/evidence/decision/', api_evidence_decision, name='teachers_api_evidence_decision'),

]
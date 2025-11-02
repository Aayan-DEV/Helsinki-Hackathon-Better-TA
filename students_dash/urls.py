from django.urls import path
from .views import dashboard, students_logout_api, api_dashboard_summary, api_exercise_group_times, api_select_group_time
from .views import exercises_page, api_exercises_full, grades_page
from .views import api_evidence_upload
from .views import extras_page

urlpatterns = [
    path('', dashboard, name='students_dashboard'),
    path('exercises/', exercises_page, name='students_exercises'),
    path('grades/', grades_page, name='students_grades'),
    path('api/exercises/full/', api_exercises_full, name='students_exercises_full'),
    path('api/logout/', students_logout_api, name='students_logout_api'),
    path('api/dashboard/summary/', api_dashboard_summary, name='students_dashboard_summary'),
    path('api/exercise/group-times/', api_exercise_group_times, name='students_exercise_group_times'),
    path('api/exercise/select-group-time/', api_select_group_time, name='students_select_group_time'),
    path('api/evidence/upload/', api_evidence_upload, name='students_evidence_upload'),
    path('extras/', extras_page, name='students_extras'),
]
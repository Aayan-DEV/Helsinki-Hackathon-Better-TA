from django.db import models
from django.conf import settings
import random

def generate_teacher_uid():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return 'TCHR-' + ''.join(random.choice(alphabet) for _ in range(8))

class TeacherCode(models.Model):
    label = models.CharField(max_length=100)
    course_name = models.CharField(max_length=150)
    special_code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} - {self.course_name} [{self.special_code}]"

class Teacher(models.Model):
    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms'),
        ('Doctor', 'Doctor'),
    ]

    code = models.ForeignKey('TeacherCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')
    user_id = models.CharField(max_length=64, blank=True, null=True, editable=False)  # Supabase user id
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_profile')
    user_uid = models.CharField(max_length=20, unique=True, editable=False, default=generate_teacher_uid)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=20, choices=TITLE_CHOICES)
    special_code = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=25, blank=True)
    email_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} {self.first_name} {self.last_name}'

class Course(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=200)
    description = models.TextField()
    students = models.ManyToManyField('students_dash.Student', related_name='courses', blank=True)
    enrolled_count = models.PositiveIntegerField(default=0)  # placeholder until enrollment model exists
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} ({self.teacher.email})'

class Exercise(models.Model):
    course = models.ForeignKey('teachers_dash.Course', on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    total_points = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} — {self.course.title}'

class ExerciseQuestion(models.Model):
    exercise = models.ForeignKey('teachers_dash.Exercise', on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    points = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'Q{self.order} ({self.points} pts) — {self.exercise.title}'

class ExerciseGroupTime(models.Model):
    exercise = models.ForeignKey('teachers_dash.Exercise', on_delete=models.CASCADE, related_name='group_times')
    name = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} @ {self.scheduled_at} — {self.exercise.title}'
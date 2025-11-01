from django.db import models
from django.conf import settings
import random

def generate_teacher_uid():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return 'TCHR-' + ''.join(random.choice(alphabet) for _ in range(8))


class TeacherCode(models.Model):
    label = models.CharField(max_length=100)            # e.g., "Math Teacher"
    course_name = models.CharField(max_length=150)      # e.g., "Math 101"
    special_code = models.CharField(max_length=50, unique=True)  # e.g., "MATH-101-XYZ"
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
    user_id = models.CharField(max_length=64, blank=True, null=True, editable=False)  # supabase user id
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_profile')
    user_uid = models.CharField(max_length=20, unique=True, editable=False, default=generate_teacher_uid)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=20, choices=TITLE_CHOICES)
    special_code = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=25, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='teacher_profile', on_delete=models.SET_NULL, null=True, blank=True)
    user_uid = models.CharField(max_length=20, unique=True, default=generate_teacher_uid, editable=False)
    email_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.title} {self.first_name} {self.last_name}'
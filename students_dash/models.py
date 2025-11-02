from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Student(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    student_id = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=128)  # Django hasher length
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password: str):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return f'{self.name} ({self.student_id})'

class StudentExerciseGroupSelection(models.Model):
    student = models.ForeignKey('students_dash.Student', on_delete=models.CASCADE, related_name='group_selections')
    exercise = models.ForeignKey('teachers_dash.Exercise', on_delete=models.CASCADE, related_name='student_group_selections')
    group_time = models.ForeignKey('teachers_dash.ExerciseGroupTime', on_delete=models.CASCADE, related_name='student_selections')
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'exercise')

    def __str__(self):
        return f'{self.student.student_id} → {self.exercise.title} @ {self.group_time.scheduled_at}'
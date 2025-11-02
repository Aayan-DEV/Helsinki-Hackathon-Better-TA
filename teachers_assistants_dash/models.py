from django.db import models

class TeachingAssistant(models.Model):
    # Global assistant directory (no course FK)
    name = models.CharField(max_length=150)
    special_code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Restored fields used by assistant APIs and signup/login flows
    email = models.EmailField(max_length=254, null=True, blank=True, unique=True)
    email_confirmed = models.BooleanField(default=False)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=20, blank=True, choices=[('Mr', 'Mr'), ('Mrs', 'Mrs'), ('Ms', 'Ms')])
    user_id = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return f'{self.name} — {self.special_code}'

class CourseAssistant(models.Model):
    course = models.ForeignKey('teachers_dash.Course', on_delete=models.CASCADE, related_name='assistants')
    assistant = models.ForeignKey('teachers_assistants_dash.TeachingAssistant', on_delete=models.CASCADE, related_name='courses')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'assistant')

    def __str__(self):
        return f'{self.course.title} — {self.assistant.name}'

class TAExerciseSession(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]
    slug = models.SlugField(max_length=32, unique=True)
    assistant = models.ForeignKey('teachers_assistants_dash.TeachingAssistant', on_delete=models.CASCADE, related_name='sessions')
    course = models.ForeignKey('teachers_dash.Course', on_delete=models.CASCADE, related_name='assistant_sessions')
    exercise = models.ForeignKey('teachers_dash.Exercise', on_delete=models.SET_NULL, null=True, blank=True, related_name='assistant_sessions')
    title = models.CharField(max_length=200, blank=True)
    time_limit_minutes = models.PositiveIntegerField(default=0)
    structure_json = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.slug} — {self.course.title} ({self.assistant.name})'

class TAExerciseSessionSubmission(models.Model):
    session = models.ForeignKey('teachers_assistants_dash.TAExerciseSession', on_delete=models.CASCADE, related_name='submissions')
    student_id = models.CharField(max_length=50)
    student_name = models.CharField(max_length=150)
    answers_json = models.JSONField(default=list)
    total_checked_count = models.PositiveIntegerField(default=0)
    group_index = models.PositiveIntegerField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    evidence_requested_at = models.DateTimeField(null=True, blank=True)
    evidence_received_at = models.DateTimeField(null=True, blank=True)
    # New: stored evidence and teacher review state
    evidence_file = models.FileField(upload_to='evidence/%Y/%m/%d/', null=True, blank=True)
    evidence_decision = models.CharField(max_length=12, blank=True)  # 'accepted' | 'declined'
    evidence_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['session', 'student_id']),
        ]

    def __str__(self):
        return f'{self.student_name} — {self.session.slug}'
from django.contrib import admin
from .models import TeachingAssistant, CourseAssistant

class CourseAssistantInline(admin.TabularInline):
    model = CourseAssistant
    extra = 0
    fields = ('course', 'assigned_at')
    readonly_fields = ('assigned_at',)

@admin.register(TeachingAssistant)
class TeachingAssistantAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'special_code',
        'assigned_courses_count',
        'signed_up',
        'added_by_teacher',
        'created_at',
    )
    search_fields = ('name', 'special_code')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    inlines = [CourseAssistantInline]

    def signed_up(self, obj):
        return bool(getattr(obj, 'user_id', None))
    signed_up.boolean = True
    signed_up.short_description = 'Signed Up'

    def added_by_teacher(self, obj):
        return not bool(getattr(obj, 'user_id', None))
    added_by_teacher.boolean = True
    added_by_teacher.short_description = 'Added by Teacher'

    def assigned_courses_count(self, obj):
        return obj.courses.count()
    assigned_courses_count.short_description = 'Assigned Courses'

@admin.register(CourseAssistant)
class CourseAssistantAdmin(admin.ModelAdmin):
    list_display = ('assistant', 'assistant_code', 'course', 'course_teacher', 'assigned_at')
    search_fields = (
        'assistant__name',
        'assistant__special_code',
        'course__title',
        'course__teacher__email',
    )
    list_filter = ('assigned_at',)

    def assistant_code(self, obj):
        return obj.assistant.special_code
    assistant_code.short_description = 'TA Code'

    def course_teacher(self, obj):
        t = obj.course.teacher
        return f'{t.title} {t.first_name} {t.last_name}'
    course_teacher.short_description = 'Teacher'
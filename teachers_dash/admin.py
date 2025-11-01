from django.contrib import admin
from .models import Teacher, TeacherCode

class TeacherInline(admin.TabularInline):
    model = Teacher
    extra = 0
    readonly_fields = ('name_and_uid', 'first_name', 'last_name', 'title', 'email', 'phone', 'created_at', 'email_confirmed')
    can_delete = False
    fields = ('name_and_uid', 'special_code', 'first_name', 'last_name', 'title', 'email', 'phone', 'email_confirmed', 'created_at')
    exclude = ('user_id', 'django_user', 'user_uid')

    def name_and_uid(self, obj):
        return f"{obj.title} {obj.first_name} {obj.last_name} — {obj.user_uid}"
    name_and_uid.short_description = 'Teacher'

@admin.register(TeacherCode)
class TeacherCodeAdmin(admin.ModelAdmin):
    list_display = ('label', 'course_name', 'special_code', 'teacher_count', 'created_at')
    search_fields = ('label', 'course_name', 'special_code')
    inlines = [TeacherInline]

    def teacher_count(self, obj):
        return obj.teachers.count()
    teacher_count.short_description = 'Teachers'

# Standalone Teacher admin for direct management
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user_uid', 'title', 'first_name', 'last_name', 'email', 'email_confirmed', 'created_at')
    search_fields = ('user_uid', 'first_name', 'last_name', 'email', 'special_code')
    readonly_fields = ('user_uid', 'user_id', 'created_at', 'email_confirmed')
    list_filter = ('email_confirmed', 'title')
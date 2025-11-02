from django.contrib import admin
from django import forms
from .models import Student

class StudentAdminForm(forms.ModelForm):
    raw_password = forms.CharField(
        label='Password',
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Set or change the password. Leave blank to keep existing.'
    )

    class Meta:
        model = Student
        fields = ['name', 'email', 'student_id', 'raw_password']

class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    list_display = ('name', 'email', 'student_id', 'created_at')
    search_fields = ('name', 'email', 'student_id')
    readonly_fields = ()
    list_filter = ('created_at',)

    def save_model(self, request, obj, form, change):
        raw = form.cleaned_data.get('raw_password') or ''
        if raw.strip():
            obj.set_password(raw.strip())
        super().save_model(request, obj, form, change)

admin.site.register(Student, StudentAdmin)
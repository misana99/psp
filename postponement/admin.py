from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(StudentRegistration)
admin.site.register(Faculty)
admin.site.register(Campus)
admin.site.register(Department)
admin.site.register(CampusDepartment)
admin.site.register(EducationLevel)
admin.site.register(Programmes)
admin.site.register(Semester)
admin.site.register(Course)
admin.site.register(AcademicYear)
admin.site.register(Student)
admin.site.register(StudentCourse)
admin.site.register(Exams)
admin.site.register(Postponement)
admin.site.register(PostponedExam)
admin.site.register(Result)
admin.site.register(ResumeStudies)

class MyModelAdmin(admin.ModelAdmin):
    list_display = ('semester', 'educationLevel')  # Columns to display in the list

admin.site.register(ScheduleSemester, MyModelAdmin)

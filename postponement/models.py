from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

def validate_dates(from_date, to_date):
    if from_date >= to_date:
        raise ValidationError("Start date must be earlier than end date.")


class Faculty(models.Model):
    facultyID = models.AutoField(primary_key=True)
    facultyName = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.facultyName


class Campus(models.Model):
    campusID = models.AutoField(primary_key=True)
    campusName = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.campusName


class Department(models.Model):
    departmentID = models.AutoField(primary_key=True)
    departmentName = models.CharField(max_length=100, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.departmentName}, {self.faculty}"


class CampusDepartment(models.Model):
    campusdepartID = models.AutoField(primary_key=True)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    HOD = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Staff'})
    
    def __str__(self):
        return f"{self.campus}, {self.department}"


class EducationLevel(models.Model):
    educationLevelD = models.AutoField(primary_key=True)
    levelName = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return f"{self.educationLevelD}, {self.levelName}"


class AcademicYear(models.Model):
    STATUS_CHOICES = [
        (0, 'Inactive'),
        (1, 'Active'),
    ]
    academicYearID = models.AutoField(primary_key=True)
    academicYearFrom = models.DateField()
    academicYearTo = models.DateField()
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)

    def clean(self):
        validate_dates(self.academicYearFrom, self.academicYearTo)
    
    def __str__(self):
        return f"{self.academicYearFrom.year}/{self.academicYearTo.year}"


class Programmes(models.Model):
    programmesID = models.AutoField(primary_key=True)
    programmeName = models.CharField(max_length=150, unique=True)
    educationLevel = models.ForeignKey(EducationLevel, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.programmesID}, {self.programmeName}, {self.educationLevel}"


class Semester(models.Model):
    semesterID = models.AutoField(primary_key=True)
    semesterName = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return f"{self.semesterName}"


class Course(models.Model):
    courseID = models.AutoField(primary_key=True)
    courseName = models.CharField(max_length=150, unique=True)
    courseCode = models.CharField(max_length=6, unique=True)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.courseName} [ {self.courseCode} ] {self.semester}"


class ScheduleSemester(models.Model):
    STATUS_CHOICES = [
        (0, 'Inactive'),
        (1, 'Active'),
    ]
    scheduleSemesterID = models.AutoField(primary_key=True)
    semesterFrom = models.DateField()
    semesterTo = models.DateField()
    educationLevel = models.ForeignKey(EducationLevel, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    academicYear = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)

    def clean(self):
        validate_dates(self.semesterFrom, self.semesterTo)
    
    def __str__(self):
        return f"{self.semester} {self.educationLevel} {self.academicYear}"


class Student(models.Model):
    registrationNumber = models.CharField(max_length=15, unique=True)
    educationLevel = models.ForeignKey(EducationLevel, on_delete=models.CASCADE)
    programme = models.ForeignKey(Programmes, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Student'})
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.registrationNumber}, {self.educationLevel}, {self.programme}"


class StudentCourse(models.Model):
    studentCourseID = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    scheduleSemester = models.ForeignKey(ScheduleSemester, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.course}"

class StudentRegistration(models.Model):
    studentRegistrationID = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    scheduleSemester = models.ForeignKey(ScheduleSemester, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student}"

class Postponement(models.Model):
    postponementID = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, default='Pending')
    activity = models.CharField(max_length=50)
    academicYear = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    requested = models.DateField(auto_now_add=True)
    scheduleSemester = models.ForeignKey(ScheduleSemester, on_delete=models.CASCADE)
    msg = models.TextField(null=True)
    reason = models.CharField(max_length=30)
    evidence = models.FileField(upload_to='evidence/', max_length=255)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE)
    expire = models.DateField(null=True)
    
    def __str__(self):
        return f"{self.student}, {self.status}, {self.activity}, {self.academicYear}"
    
class ResumeStudies(models.Model):
    postponement = models.OneToOneField(Postponement, on_delete=models.CASCADE)
    resumed = models.DateField(auto_now_add=True)
    attachement = models.FileField(upload_to='resume/', max_length=255)
    resume_status = models.CharField(max_length=20, default="Pending")
    resume_requested = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.postponement}, {self.resumed}, {self.attachement}"


class Exams(models.Model):
    STATUS_CHOICES = [
        (0, 'Inactive'),
        (1, 'Active'),
    ]
    examID = models.AutoField(primary_key=True)
    scheduleSemester = models.ForeignKey(ScheduleSemester, on_delete=models.CASCADE)
    examStartFrom = models.DateField()
    educationLevel = models.ForeignKey(EducationLevel, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.scheduleSemester}, {self.examStartFrom}, {self.educationLevel}"


class PostponedExam(models.Model):
    postponedExamID = models.AutoField(primary_key=True)
    postponement = models.ForeignKey(Postponement, on_delete=models.CASCADE)
    course = models.ForeignKey(StudentCourse, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.postponedExamID}, {self.postponement}, {self.course}"
    
class Result(models.Model):
    cw = models.CharField(max_length=3)
    ue = models.CharField(max_length=3)
    scheduleSemester = models.ForeignKey(ScheduleSemester, on_delete=models.CASCADE) 
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.cw}, {self.ue}"


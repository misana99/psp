from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from django.utils.timezone import now
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.utils import IntegrityError
from django.urls import reverse

# Create your views here.
def landing(req):
    # student id & aducation level
    student_id_level = Student.objects.values('id','educationLevel','campus').filter(user=req.user.id).first()

     # postponement records
    postponements = Postponement.objects.values('status', 'postponementID', 'student__registrationNumber', 'activity', 'requested', 'reason', 'evidence', 'msg', 'scheduleSemester__semester__semesterName', 'academicYear__academicYearFrom', 'academicYear__academicYearTo').filter(student_id=student_id_level['id'])

    data = {
        'postponement' : postponements,
        'MEDIA_URL': settings.MEDIA_URL
    }

    print(postponements)

    return render(req, 'student_info.html', data)

def request_postponement(req):
    if not req.user.is_authenticated or not req.user.groups.filter(name='Student').exists():
        return redirect('signin')
    
    # student id & aducation level
    student_id_level = Student.objects.values('id','educationLevel','campus').filter(user=req.user.id).first()

    # active academic year
    currentAcademicYear = AcademicYear.objects.values('academicYearID').filter(status=1).first()

    if req.method == 'POST':
        # current date
        today = now().date()

        # semester period
        semesterStart = ScheduleSemester.objects.values('semesterFrom').filter(academicYear = currentAcademicYear['academicYearID'], educationLevel=student_id_level['educationLevel'], status=1).first()
        semesterEnd = ScheduleSemester.objects.values('semesterTo').filter(academicYear = currentAcademicYear['academicYearID'], educationLevel=student_id_level['educationLevel'], status=1).first()

        semester_start_date = semesterStart['semesterFrom'] if semesterStart else None
        semester_end_date = semesterEnd['semesterTo'] if semesterEnd else None
        #########################

        #academic year period
        acFrom = AcademicYear.objects.values('academicYearFrom').filter(academicYearID = currentAcademicYear['academicYearID']).first()
        acTo = AcademicYear.objects.values('academicYearTo').filter(academicYearID = currentAcademicYear['academicYearID']).first()

        ac_start_date = acFrom['academicYearFrom'] if acFrom else None
        ac_end_date = acTo['academicYearTo'] if acTo else None

        start_date = ac_start_date + relativedelta(years=1)
        end_date = ac_end_date + relativedelta(years=1)
        #########################

        # input values from form in view template
        save_activity = req.POST.get('option') # Studies / Examination
        save_semister = req.POST.get('semester') # semester ID
        reason = req.POST.get('reason') 

        if not save_semister:
            messages.error(req, "There is no active semester selected.")
            return redirect("pspn:create")

        if not req.FILES.get('evidence'):
            messages.error(req, "Evidence to support your reason is required")
            return redirect("pspn:create")
        
        evidence = req.FILES['evidence']

        # check if file is PDF
        if not evidence.name.endswith('.pdf'):
            messages.error(req, "Only PDF files are allowed")
            return redirect("pspn:create")
        
        # check if file size is <= 2MB
        if not evidence.size <= 2 * 1024 * 1024:
            messages.error(req, "File size should not exceed 2MB")
            return redirect("pspn:create")
        
        try:
            # object instance for saving
            student = Student.objects.get(id=student_id_level['id'])
            academic = AcademicYear.objects.filter(status=1).get(academicYearID=currentAcademicYear['academicYearID'])
            sem_inst = ScheduleSemester.objects.get(scheduleSemesterID=save_semister)
            campus = Campus.objects.get(campusID = student_id_level['campus'])
        except Student.DoesNotExist:
            messages.error(req, "Student not found.")
            return redirect("pspn:create")
        except AcademicYear.DoesNotExist:
            messages.error(req, "Active academic year not found.")
            return redirect("pspn:create")
        except ScheduleSemester.DoesNotExist:
            messages.error(req, "Selected semester does not exist.")
            return redirect("pspn:create")
        except Campus.DoesNotExist:
            messages.error(req, "Campus not found.")
            return redirect("pspn:create")
        
        def maxPostponement(student, activity):
            counted = Postponement.objects.filter(student=student, activity= activity).count()
            return counted
        
        def postponementYealy(student, activity, year):
            counted = Postponement.objects.filter(student=student, activity= activity, academicYear = year).count()
            return counted
        
        def postponementInSemester(student, activity, year, semester):
            counted = Postponement.objects.filter(student=student, activity= activity, academicYear = year, scheduleSemester=semester).count()
            return counted
        
        def postponementExamAfterStudies(student, activity, year, semester):
            counted = Postponement.objects.filter(student=student, activity= activity, academicYear = year, scheduleSemester=semester).count()
            return counted
        
        if save_activity == "Studies":
            # check if student already postpone studies during this year
            if postponementYealy(student_id_level['id'], save_activity, currentAcademicYear['academicYearID']) >= 1:
                messages.error(req, "Postponement of studies is allowed once per academic year")
                return redirect('pspn:create')
            
            # limit student to postpone studies only twice
            if maxPostponement(student_id_level['id'], save_activity) >= 2:
                messages.error(req, "Postponement of studies is limited to twice throughout your studies")
                return redirect('pspn:create')
            
            # postponement of studies can be taken 3 weeks teach period end
            check_3_week = semester_end_date - timedelta(weeks=3)

            if not reason == "Health problem":
                if today > check_3_week:
                    messages.error(req, "Postponement is not allowed in the last three weeks of the semester.")
                    return redirect('pspn:create')
            
            # postponement of studies can be taken within the semester period
            if not (semester_start_date <= today <= semester_end_date):
                messages.error(req, "Postponement can only be requested during the semester period.")
                return redirect("pspn:create")
            
            # check if student already postpone examination before studies
            if postponementYealy(student_id_level['id'], 'Examination', currentAcademicYear['academicYearID']) >= 1:
                messages.error(req, "You cannot postpone studies after postponing examination")
                return redirect('pspn:create')

            # check semesters to optimize notice
            try:
                check_sem = ScheduleSemester.objects.values('semester__semesterName').filter(scheduleSemesterID=save_semister).first()
            except ScheduleSemester.DoesNotExist:
                messages.error(req, "Selected semester does not exist.")
                return redirect("pspn:create")
            
            if check_sem['semester__semesterName'] == "Semester one":
                msg = f"You're eligible to resume studies on {start_date.year}/{end_date.year} academic year"
            elif check_sem['semester__semesterName'] == "Semester two":
                try:
                    sem_one = ScheduleSemester.objects.values('scheduleSemesterID').filter(
                    semester__semesterName="Semester one",
                    academicYear=currentAcademicYear['academicYearID'],
                    educationLevel=student_id_level['educationLevel']
                    ).first()
                    results = Result.objects.values('student', 'scheduleSemester', 'cw', 'ue').filter(
                        scheduleSemester=sem_one['scheduleSemesterID'], student=student_id_level['id']
                    ).first()
                except ScheduleSemester.DoesNotExist:
                    messages.error(req, "System can't find what you're looking")
                    return redirect('pspn:create')
                except Result.DoesNotExist:
                    messages.error(req, "Student results are missing")
                    return redirect('pspn:create')

                cw = results.get('cw')
                ue = results.get('ue')

                if not (cw == "Yes" and ue == "Yes"):
                    messages.error(req, "You are not eligible for postponement as your last semester results are missing!")
                    return redirect('pspn:create')
                
            exp =  ac_start_date + relativedelta(months=4)

            msg = f"You're eligible to resume studies on {check_sem['semester__semesterName']} of {start_date.year}/{end_date.year} academic year"
            Postponement.objects.create(student=student, activity=save_activity, academicYear=academic, scheduleSemester=sem_inst, msg=msg, reason=reason, evidence=evidence, campus=campus, expire=exp)
            messages.success(req, f"{save_activity} postponement request sent.")
            return redirect('pspn:home')

        elif save_activity == "Examination":
            selected_courses = req.POST.getlist('selected_course')
            if not selected_courses:
                messages.error(req, "No courses selected!")
                return redirect('pspn:create')

            try:
                courses = Course.objects.filter(courseID__in=selected_courses)
                stdCourse = StudentCourse.objects.filter(course__in=courses, student=student_id_level['id'])
                results = Result.objects.values('student', 'scheduleSemester', 'cw').filter(scheduleSemester=save_semister, student=student_id_level['id']).first()
            except Course.DoesNotExist:
                messages.error(req, f"Selected courses doesn't match any of our records")
                return redirect('pspn:create')
            except StudentCourse.DoesNotExist:
                messages.error(req, f"Selected courses doesn't match any of your registered courses")
                return redirect('pspn:create')
            except Result.DoesNotExist:
                messages.error(req, "Student results are missing")
                return redirect('pspn:create')
            
            if postponementExamAfterStudies(student_id_level['id'], "Studies", currentAcademicYear['academicYearID'], save_semister):
                messages.error(req, "You cannot postpone Examination after postponing studies")
                return redirect('pspn:create')

            if postponementInSemester(student_id_level['id'], save_activity, currentAcademicYear['academicYearID'], save_semister) >= 1:
                messages.error(req, "You cannot postpone Examination twice per semester")
                return redirect('pspn:create')

            if results is None:
                messages.error(req, "Missing results!")
                return redirect('pspn:create')
        
            cw = results.get('cw')


            if not cw == "Yes":
                messages.error(req, "You are not eligible for postponement as your course work results are missing!")
                return redirect('pspn:create')

            exams_start = Exams.objects.values('examStartFrom').filter(scheduleSemester = save_semister, educationLevel=student_id_level['educationLevel']).first()
            exam_start_date = exams_start['examStartFrom'] if exams_start else None
            check_1_week = exam_start_date - timedelta(weeks=1)

            if not reason == "Health problem":
                if today > check_1_week:
                    messages.error(req, "Examination postponement is not allowed in the last week before the examination begin.")
                    return redirect('pspn:create')
            
            msg = "Your postponed examination will be held during supplimentary and special examination period."

            try:
                with transaction.atomic():
                    postponement = Postponement.objects.create(student=student, activity=save_activity, academicYear=academic, scheduleSemester=sem_inst, msg=msg, reason=reason, evidence=evidence, campus=campus)

                    postponed_exams = [PostponedExam(postponement=postponement, course=course) for course in stdCourse]

                    PostponedExam.objects.bulk_create(postponed_exams)
                    messages.success(req, f"{save_activity} postponement request sent.")
            except Exception as e:
                messages.error(req, f"Transaction failed: {e}")
                return redirect('pspn:home')

            return redirect('pspn:home')

        else:
            messages.info(req, "Requested operation not recognized!")
            return redirect('pspn:create')

    # semetsers in current year with education level
    semester = ScheduleSemester.objects.values('semester__semesterName','status','scheduleSemesterID').filter(academicYear = currentAcademicYear['academicYearID'], educationLevel=student_id_level['educationLevel'], status=1)

    # student course for the active semister/academic year
    semesterID = None

    for sem in semester:
        if(sem['status'] == 1):
            semesterID = sem['scheduleSemesterID']

    modules = StudentCourse.objects.values('course__courseID','course__courseName','student','scheduleSemester').filter(student_id=student_id_level['id'], scheduleSemester=semesterID)
    # end

    data = {
        'semester' : semester,
        'modules' : modules,
    }

    return render(req, 'new_request.html', data)

def activity(req, pk):
    data = PostponedExam.objects.values('course__course__courseName', 'course__course__courseCode', 'postponement__msg').filter(postponement=pk)
    unique_msgs = {exam['postponement__msg'] for exam in data}
    return render(req, 'activity.html', {'data': data, "msg": unique_msgs})

def activity_two(req, pk):
    if req.method == "POST":
        if not req.FILES.get('attachement'):
            messages.error(req, "Resuming studies must come with latter")
            return redirect(reverse('pspn:activity_two', args=[pk]))
        
        attachement = req.FILES['attachement']

        # check if file is PDF
        if not attachement.name.endswith('.pdf'):
            messages.error(req, "Only PDF files are allowed")
            return redirect(reverse('pspn:activity_two', args=[pk]))
        
        # check if file size is <= 2MB
        if not attachement.size <= 2 * 1024 * 1024:
            messages.error(req, "File size should not exceed 2MB")
            return redirect(reverse('pspn:activity_two', args=[pk]))
        postponementIDInstance = Postponement.objects.get(postponementID=pk)

        # current date
        today = now().date()

        if not postponementIDInstance.expire >= today: 
            messages.error(req, f"You cannot resume studies before {postponementIDInstance.expire}")
            return redirect(reverse('pspn:activity_two', args=[pk]))
        else:
            if postponementIDInstance.status == "Pending" or postponementIDInstance.status == "Rejected":
                messages.error(req, "You cannot resume because it was never approved.")
                return redirect(reverse('pspn:activity_two', args=[pk]))

            try:
                ResumeStudies.objects.create(postponement=postponementIDInstance, attachement=attachement)
                messages.success(req, "Congraturation! you're studies has been resumed")
                return redirect(reverse('pspn:activity_two', args=[pk]))
            except IntegrityError as e:
                messages.error(req, "This postponement has already resumed")
                return redirect(reverse('pspn:activity_two', args=[pk]))
            except Exception as e:
                messages.error(req, "This postponement has already resumed")
                return redirect(reverse('pspn:activity_two', args=[pk]))

    data = Postponement.objects.values('msg','scheduleSemester__semester__semesterName').get(postponementID=pk)
    return render(req, 'activity_two.html', {'data': data})

def hod(req):
    if not req.user.is_authenticated or not req.user.groups.filter(name='Staff').exists():
        return redirect('signin')
    
    try:
         hod = CampusDepartment.objects.values('campus','department').filter(HOD=req.user.id).first()
    except CampusDepartment.DoesNotExist:
        messages.error(req, "HOD Not found")
        return redirect("pspn:hod")
    
    if req.method == 'POST':
        status = req.POST.get('verification')
        msg = req.POST.get('reason-rejection')
        id = req.POST.get('postponement')

        if not status:
            messages.error(req, "Status field is require")
            return redirect("pspn:hod")

        if status == "Rejected":
            if not msg:
                messages.error(req, "Rejection comment field is require")
                return redirect("pspn:hod")
            Postponement.objects.filter(postponementID=id).update(status=status, msg=msg)
            messages.success(req, "Postponement request rejected")
            return redirect("pspn:hod")

        Postponement.objects.filter(postponementID=id).update(status=status)
        messages.success(req, "Postponement request accepted")
        return redirect("pspn:hod")
 
    postponements = Postponement.objects.values('status', 'campus__campusdepartment__department','postponementID', 'student__registrationNumber', 'activity', 'requested', 'reason', 'evidence', 'msg', 'scheduleSemester__semester__semesterName', 'academicYear__academicYearFrom', 'academicYear__academicYearTo').filter(campus=hod['campus'], campus__campusdepartment__department=hod['department']).order_by('-requested')
 
    context = {
        'postponement' : postponements,
        'MEDIA_URL': settings.MEDIA_URL,
    } 
    return render(req, 'hod.html', context)

def resume(req):
    try:
         hod = CampusDepartment.objects.values('campus','department').filter(HOD=req.user.id).first()
    except CampusDepartment.DoesNotExist:
        messages.error(req, "HOD Not found")
        return redirect("pspn:hod")
    
    if req.method == 'POST':
        status = req.POST.get('verification')
        msg = req.POST.get('reason-rejection')
        id = req.POST.get('resume')

        if not status:
            messages.error(req, "Status field is require")
            return redirect("pspn:resume")

        if status == "Rejected":
            if not msg:
                messages.error(req, "Rejection comment field is require")
                return redirect("pspn:resume")
            
            ResumeStudies.objects.filter(id=id).update(resume_status=status, msg=msg)
            messages.success(req, "Resume studies request rejected")
            return redirect("pspn:resume")
        
        ResumeStudies.objects.filter(id=id).update(resume_status=status)
        messages.success(req, "Resume request aapproved")
        return redirect("pspn:resume")

    data = ResumeStudies.objects.values('id','postponement__student__registrationNumber', 'resume_requested', 'resume_status', 'attachement', 'postponement__campus', 'postponement__campus__campusdepartment__department').filter(postponement__campus=hod['campus'], postponement__campus__campusdepartment__department=hod['department']).order_by('-resume_status')
    context = {
        'data' : data,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(req, 'resume.html', context)

def dash(req):
    try:
         hod = CampusDepartment.objects.values('campus','department').filter(HOD=req.user.id).first()
    except CampusDepartment.DoesNotExist:
        messages.error(req, "HOD Not found")
        return redirect("pspn:hod")
    
    t_postponement = Postponement.objects.filter(campus=hod['campus'], campus__campusdepartment__department=hod['department']).count()
    e_postponement = Postponement.objects.filter(activity="Examination",campus=hod['campus'], campus__campusdepartment__department=hod['department']).count()
    s_postponement = Postponement.objects.filter(activity="Studies",campus=hod['campus'], campus__campusdepartment__department=hod['department']).count()
    r_postponement = Postponement.objects.filter(status="Rejected",campus=hod['campus'], campus__campusdepartment__department=hod['department']).count()

    context = {
        'total_postponement' : t_postponement,
        'exams_postponement' : e_postponement,
        'studies_postponement' : s_postponement,
        'rejected_postponement' : r_postponement
    }
    return render(req, 'dash.html', context)

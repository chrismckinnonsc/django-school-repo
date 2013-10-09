from django.test import TestCase
from school.models import Semester, StaffMember, Department, Subject, SchoolClass, Student, Enrolment
from sync.google_admin import GoogleSync
from django.conf import settings
import datetime

#class SchoolTest(TestCase):
class SchoolTest(TestCase):
    def setUp(self):
        #import pdb
        #pdb.set_trace()
        self.google_sync = GoogleSync()

        self.sem, c = Semester.objects.get_or_create(number=1, year="2013",
                                       start_date=datetime.date(2013,1,29), end_date=datetime.date(2013,6,7))
        self.tch, c = StaffMember.objects.get_or_create(
                                                     first_name="John", last_name="Teacher",
                                                     email="john.teacher@" + settings.GOOGLE_APPS_DOMAIN,
                                                     date_of_birth=datetime.date(1970,3,3), timetable_id="XTCH",
                                                     is_current=True,
                                                     staff_type="TEA"
                                                     )
        #self.google_sync.update_google_staff(self.tch)
        self.dept, c = Department.objects.get_or_create(name="Test Faculty")
        self.subj, c = Subject.objects.get_or_create(code="14XTST", name="Test Subject", faculty=self.dept)
        self.cla, c = SchoolClass.objects.get_or_create(code="14XTSTB", name="Test Class B", cycle=self.sem,
                                                     teacher=self.tch, subject=self.subj)
        self.students = []
        for i in range(1,5):
            id='XTST%04d' % i
            s, c = Student.objects.get_or_create(
                                             first_name="Test%d"%i, last_name="Student%d"%i,
                                             email="%s@%s" % (id, settings.GOOGLE_APPS_DOMAIN),
                                             date_of_birth=datetime.date(2000,3,(i%27)+1), timetable_id=id,
                                             is_current=True,
                                             student_type="STU", year_level="14"
                                             )
            #self.google_sync.update_google_student(s)
            Enrolment.objects.get_or_create(student=s, school_class=self.cla)
            self.students.append(s)

    # def test_student_create(self):
    #     pass
    #
    # def test_student_update(self):
    #     pass
    #
    # def test_student_exit(self):
    #     pass
    #
    # def test_staff_create(self):
    #     pass
    #
    # def test_staff_update(self):
    #     pass
    #
    # def test_staff_exit(self):
    #     pass
    #
    # def test_class_create(self):
    #     pass
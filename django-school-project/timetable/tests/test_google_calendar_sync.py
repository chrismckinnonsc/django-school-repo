from django.test import TestCase
import datetime
from school.models import SchoolClass, Student, StaffMember, Semester, Department, Subject
from school.tests.test_school import SchoolTest
from timetable.models import Term, Day, Date, Entry, Event, Location

class GoogleTTCalendarSyncTest(SchoolTest):
    def setUp(self):
        super(GoogleTTCalendarSyncTest, self).setUp()
        self.term = Term.objects.get_or_create(number=2, year="2013", start_week=2,
                                   start_date=datetime.date(2013,4,15), end_date=datetime.date(2013,6,28))
        self.entries = []
        cla = SchoolClass.objects.all()[0]
        for i in range(10):
            d = Day.objects.all()[i % Day.objects.count()]
            p=d.periods.all()[i % d.periods.count()]
            entry,c = Entry.objects.get_or_create(day=d, period=p, school_class=cla)

    def test_nothing(self):
        pass
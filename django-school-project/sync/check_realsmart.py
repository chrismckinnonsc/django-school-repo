from school.models import *
import csv
import tempfile
import logging
logger = logging.getLogger(__name__)


def check_realsmart(InFile=None):
    if not InFile:
        InFile = 'realsmartexport.csv'
    myfile = open(InFile)
    reader = csv.DictReader(myfile)
    rs_students = {}
    rs_teachers = {}
    for row in reader:
        if row['Learner/Mentor'] == 'learner':
            rs_students[row['Username'].upper()] = row
        elif row['Learner/Mentor'] == 'mentor' or row['Learner/Mentor'] == 'admin':
            rs_teachers[row['Username'].upper()] = row
            if row['Username'] == "woo":
                print row

    for s in Student.objects.filter(is_current=True):
        if s.timetable_id in rs_students:
            rss = rs_students[s.timetable_id]
            if rss['Status'] == 'SUSPENDED':
                print "student %s has suspended status" % s.timetable_id
            if s.last_name.upper() == rss['Surname'].upper():
                if not (s.first_name.upper() == rss['Forename'].upper() or s.preferred_name.upper() == rss['Forename'].upper()):
                    print "student %s doesn't match first name. local: %s/%s. RS: %s" % (s.timetable_id, s.first_name, s.preferred_name, rss['Forename'])
            else:
                print "student %s doesn't match surname. local: %s. RS: %s" % (s.timetable_id, s.last_name, rss['Surname'])
        else:
            print "student %s (%s %s) not in RS data" % (s.timetable_id, s.first_name, s.last_name)

    for s in StaffMember.objects.filter(is_current=True):
        if s.timetable_id in rs_teachers:
            rss = rs_teachers[s.timetable_id]
            if rss['Status'] == 'SUSPENDED':
                print "teacher %s has suspended status" % s.timetable_id
            if s.last_name.upper() == rss['Surname'].upper():
                if not (s.first_name.upper() == rss['Forename'].upper() or s.preferred_name.upper() == rss['Forename'].upper()):
                    print "teacher %s doesn't match first name. local: %s/%s. RS: %s" % (s.timetable_id, s.first_name, s.preferred_name, rss['Forename'])
            else:
                print "teacher %s doesn't match surname. local: %s. RS: %s" % (s.timetable_id, s.last_name, rss['Surname'])
        else:
            print "teacher %s (%s %s) not in RS data" % (s.timetable_id, s.first_name, s.last_name)

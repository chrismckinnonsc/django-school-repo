import xml.etree.ElementTree as ET
import httplib, urllib
from urlparse import urlparse
from school.models import Student, StaffMember, SchoolClass, Semester
from django.conf import settings
import os

import logging
logger = logging.getLogger(__name__)


def add_realsmart_xml_record(parent, record_dict):
    record = ET.SubElement(parent, "Record")
    for k,v in record_dict.iteritems():
        elem = ET.SubElement(record,k)
        elem.text = v
    return record

def post_realsmart_xml(xml, authkey, uri):
    parsed_uri = urlparse(uri)
    params = urllib.urlencode({"authKey": authkey, "xmlString": xml})
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    conn = httplib.HTTPSConnection(parsed_uri.netloc)
    conn.request("POST", parsed_uri.path, params, headers)
    res = conn.getresponse()

    logger.info("%s %s" % (res.status, res.reason)) #TODO - parse status and reason
    data = res.read()
    logger.info(data)

def export_rs_password_csv():
    students = Student.objects.filter(is_current=True)
    f = open("rs_pw.csv", "w")
    for u in students:
        f.write("%s,%s,%s,%s,%s,%s\n" % (u.timetable_id, u.last_name, u.first_name, u.year_level, u.mentor_group, u.initial_password ))
    f.close()

def export_realsmart(request=None):
    rs_key = open(os.path.join(settings.SECRETS_PATH, "realsmart_key.txt")).readline().strip() #TODO - catch exceptions

    learners_root = ET.Element("SuperStarReport")

    students = Student.objects.filter(is_current = True)
    for u in students:
        classes = SchoolClass.objects.filter(students=u, cycle=Semester.working(request))
        for c in classes:
            rec_dict = {
                #"multiple_id": str(u.id) + ",", #TODO - should hide id from outside world; replace with???
                "Surname": u.last_name,
                "Forename": u.first_name,
                "Username": u.timetable_id,
                "UPN": u.govt_student_code,
                "Year": u.year_level,
                "Reg": u.mentor_group,
                "Class": c.code,
                "SubjectCode": c.subject.code,
                "Subject": c.subject.name,
                }
            #if u.InitialPassword:
            #    rec_dict['Password'] = u.InitialPassword
            if not u.govt_student_code or u.govt_student_code == "UNKNOWN":
                #rec_dict['Password'] = u.InitialPassword
                rec_dict['UPN'] = str(u.id)
            add_realsmart_xml_record(learners_root,rec_dict)


    learners_xml = ET.tostring(learners_root)
    l = open('learners.xml','w')
    l.write(learners_xml)
    l.close()

    post_realsmart_xml(learners_xml, rs_key, settings.REALSMART_LEARNER_URI)

    mentors_root = ET.Element("SuperStarReport")
    teachers = StaffMember.objects.filter(is_current=True)
    for u in teachers:
        classes = SchoolClass.objects.filter(teacher=u, cycle=Semester.working(request))
        for c in classes:
            rec_dict = {
                #"multiple_id": str(u.id) + ",", #TODO - should hide id from outside world; replace with???
                "FullName": "%s %s %s" % (u.title, u.first_name[0], u.last_name),
                "Title": u.title,
                "Surname": u.last_name,
                "Initials": u.timetable_id,
                "Forename": u.first_name,
                "Username": u.timetable_id,
                #"Password": s.,
                "Class": c.code,
                "SubjectCode": c.subject.code,
                "Subject": c.subject.name,
                }
            add_realsmart_xml_record(mentors_root,rec_dict)
    mentors_xml = ET.tostring(mentors_root)
    l = open('mentors.xml','w')
    l.write(mentors_xml)
    l.close()

    post_realsmart_xml(mentors_xml, rs_key, settings.REALSMART_MENTOR_URI)

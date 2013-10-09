from school.models import *
from timetable.models import *
from django.db import IntegrityError
from django.conf import settings
import csv
import random
import datetime
import string
import logging
logger = logging.getLogger(__name__)

def fix_date(date):
    '''Converts DD/MM/YYYY to YYYY-MM-DD'''
    d = date.split("/")
    d.reverse()
    return "-".join(d)

def import_students(Filehandle):
    '''Imports students from a CASES csv export'''
    reader = csv.DictReader(Filehandle)
    file_students = [] #list of student IDs in the file being processed
    for row in reader:
        if not row["ST.STKEY"]:
            logger.warn("No CASES ID detected for line %d in student import" % reader.line_num)
            continue #skip row if no CASES ID
        try:
            file_students.append(row["ST.STKEY"])
        except KeyError:
            logger.warn("No CASES ID detected for line %d in student import" % reader.line_num)
            continue #skip row if no CASES ID
        try:
            s = Student.objects.get(timetable_id__exact = row["ST.STKEY"])
        except Student.DoesNotExist:
            s = Student()
            s.timetable_id=row["ST.STKEY"]
            logger.info("creating student %s" % row["ST.STKEY"])
        s.email = "%s@%s" % (row["ST.STKEY"], settings.GOOGLE_APPS_DOMAIN)
        s.first_name = row["ST.FIRST_NAME"]
        s.middle_name = row["ST.SECOND_NAME"]
        s.last_name = row["ST.SURNAME"]
        s.preferred_name = row["ST.PREF_NAME"]
        s.govt_student_code = row["ST.VSN"]
        if s.govt_student_code == "UNKNOWN":
            s.govt_student_code = s.timetable_id #TODO - fix ugly workaround for non-existent VSN
            logger.info("Student %s missing VSN in import data" % s.timetable_id)
        s.uni_application_code = row["ST.VCE_ID"]
        s.gender = row["ST.GENDER"]
        s.title = row["ST.TITLE"]
        s.year_level = row["ST.SCHOOL_YEAR"]
        s.date_of_birth = fix_date(row["ST.BIRTHDATE"])
        s.mobile_number = row["ST.MOBILE"]
        try:
            if s.mobile_number[0] != "0": #fix for stupid Excel cutting leading 0 off mobile field
                s.mobile_number = "0" + s.mobile_number
        except IndexError: #if MobileNumber not populated, indexing it will fail
            pass
        s.start_date = fix_date(row["ST.ENTRY"])

        # TODO - deal with FUT (future student) and others?
        if row["ST.STATUS"] == "ACTV" or row["ST.STATUS"] == "LVNG":
            s.is_current = True
        else:
            s.end_date = datetime.date.today()
            s.is_current = False

        s.address1 = row["UM.ADDRESS01"]
        s.address2 = row["UM.ADDRESS02"]
        s.address3 = row["UM.ADDRESS03"]
        s.post_code = row["UM.POSTCODE"]
        s.state = row["UM.STATE"]
        s.country = "Australia"
        s.home_number = row["UM.TELEPHONE"]

        if row["ST.STKEY"][0:3] == "NWP":
            s.student_type = "EXC"
        else:
            s.student_type = "STU"

        if not s.initial_password:
            s.initial_password = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(8))

        #TODO - validate
        s.mentor_group = row["ST.HOME_GROUP"]
        s.house_group = row["ST.HOUSE"]

        #TODO - log update
        s.save()


    '''
    #iterate over students in DB to check for students not in the file - POTENTIALLY DANGEROUS
    for s in Student.objects.all():
        if not s.timetable_id in file_students:
            logger.info("student %s not in import data; setting as not current" % s.timetable_id)
            s.end_date = datetime.today()
            s.is_current = False
            s.save()
    '''

def import_mds_file_students(MDSFile):
    '''import MDS attributes from supplied MDS file'''
    reader = csv.DictReader(open(MDSFile))
    for row in reader:
        try:
            s = Student.objects.get(timetable_id__exact = row["CASES ID"])
        except Student.DoesNotExist:
            logger.warning("Importing MDS: student %s doesn't exist in Database" % row["CASES ID"])
            continue
        try:
            s.network_id = row["username"]
        except KeyError:
            s.network_id = row["Authcate"]
        try:
            s.initial_password = row["password"] #TODO - do we need multiple initial password fields for authcate, RS, Google?
        except KeyError:
            pass
        #TODO - log update
        s.save()

def import_mds_file_staff(MDSFile):
    '''import MDS attributes from supplied MDS file'''
    reader = csv.DictReader(open(MDSFile))
    for row in reader:
        try:
            s = StaffMember.objects.get(timetable_id__exact = row["CASES ID"])
        except StaffMember.DoesNotExist:
            logger.warning("Importing MDS: staffmember %s doesn't exist in Database" % row["CASES ID"])
            continue
        try:
            s.network_id = row["username"]
        except KeyError:
            s.network_id = row["Authcate"]
        try:
            s.initial_password = row["password"] #TODO - do we need multiple initial password fields for authcate, RS, Google?
        except KeyError:
            pass
        #TODO - log update
        s.save()


def import_staff(StaffFile):
    '''Imports staff from a CASES csv export'''
    #TODO -add lots more fields here
    staffreader=csv.DictReader(StaffFile)
    for row in staffreader:
        if not row["SF.SFKEY"]:   #skip if no CASES ID
            continue
        try:
            teacher = StaffMember.objects.get(timetable_id__exact = row["SF.SFKEY"])
        except StaffMember.DoesNotExist:
            if row["SF.STAFF_STATUS"] == "INAC" or row["SF.STAFF_STATUS"] == "LEFT": #don't create new inactive users
                continue
            teacher = StaffMember()
            teacher.timetable_id = row["SF.SFKEY"]
            logger.info("creating staff member %s" % row["SF.SFKEY"])
        teacher.email = "%s@%s" % (row["SF.SFKEY"], settings.GOOGLE_APPS_DOMAIN)
        teacher.govt_email_address = row["SF.E_MAIL"]
        teacher.first_name = row["SF.FIRST_NAME"]
        teacher.middle_name = row["SF.SECOND_NAME"]
        teacher.preferred_name = row["SF.PREF_NAME"]
        teacher.last_name = row["SF.SURNAME"]
        teacher.gender = row["SF.GENDER"]
        teacher.title = row["SF.TITLE"]
        if row["SF.BIRTHDATE"]:
            teacher.date_of_birth = fix_date(row["SF.BIRTHDATE"])
        else:
            teacher.date_of_birth = "1900-01-01"
        teacher.govt_id_number = row["SF.PAYROLL_REC_NO"]

        if row["SF.START"]:
            teacher.start_date = fix_date(row["SF.START"])
        teacher.mobile_number = row["SF.MOBILE"]
        if row["SF.STAFF_STATUS"] == "INAC" or row["SF.STAFF_STATUS"] == "LEFT":
            #TODO - set EndDate if not already set
            teacher.is_current = False
        else:
            teacher.is_current = True
        if row["SF.HOUSE"]:
            teacher.house_group = row["SF.HOUSE"]

        if not teacher.initial_password:
            teacher.initial_password = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(8))

        teacher.save()

def import_rs_mis(ImportFile):
    reader = csv.DictReader(ImportFile)
    for row in reader:
        if row['Learner/Mentor'] == 'mentor':
            u = StaffMember.objects.get(timetable_id_iexact=row['Username'])
            #u.rs_mis_id =

def import_staff_misc(StaffFile):
    '''import misc staff attributes'''
    staffreader=csv.DictReader(StaffFile)
    for row in staffreader:
        if not row["CASES ID"]:   #skip if no CASES ID
            continue
        try:
            teacher = StaffMember.objects.get(timetable_id__exact = row["CASES ID"])
        except StaffMember.DoesNotExist:
            continue
        teacher.email = row["School email"]
        teacher.network_id = row["Authcate"]
        teacher.save()

def import_enrolments_from(EnrolmentsFile, request=None):
    '''import enrolments from Timetabler data file'''

    enrolment_reader = csv.DictReader(EnrolmentsFile)
    current_cycle = Semester.working()

    #TODO - go through current classes and remove non-existent ones?

    # Create internal list initially
    class_lists = {}
    tt_entries = []
    for row in enrolment_reader:
#        if not (row["Class Code"] == "10TEMTg" or row["Class Code"] == "11HFREa"):
#            continue
        if row["Class Code"][0:4] == "MENT":
            subject_code = "MENT"
            faculty_code = "Wellbeing"
            class_code = row["Class Code"]
#        elif row["Class Code"][0:6] == "11SMCP": #ugly hack for non-consistent coding
#            subject_code = "11SMCP"
#            faculty_code = "S"
#            class_code = subject_code + row["Class Code"][-1]
        elif row["Class Code"][0:3] == "CCR":
            subject_code = row["Class Code"]
            faculty_code = "Co-curricular"
            class_code = row["Class Code"]
        else:
            subject_code = row["Class Code"][0:-1]
            faculty_code = row["Class Code"][2:3]
            class_code = row["Class Code"]
        try:
            class_lists[class_code]['students'].append(row["Student Code"])
        except KeyError:
            class_lists[class_code] = {'teacher': row["Teacher Code"],
                                       'subject': subject_code,
                                       'faculty': faculty_code,
                                       'students': []}
            class_lists[class_code]['students'].append(row["Student Code"])

        #read in timetable
        tt_entry = (row["Day No"], row["Period No"], row["Room Code"], row["Class Code"])
        if not tt_entry in tt_entries:
            tt_entries.append(tt_entry)

    # add classes and enrolments to DB
    for class_code, class_details in class_lists.iteritems():
        logger.info("processing class %s" % class_code)
        try:
            teacher = StaffMember.objects.get(timetable_id=class_details['teacher'])
        except StaffMember.DoesNotExist:
            logger.error("Could not find teacher %s; cannot create class %s" % (class_details['teacher'], class_code))
            continue #TODO - Should we still try to create the class without a teacher?

        try:
            class_obj = SchoolClass.objects.get(code=class_code, cycle=current_cycle)
            class_obj.teacher = teacher
            class_obj.save()
        except SchoolClass.DoesNotExist:
            try:
                subject_obj = Subject.objects.get(code=class_details['subject'])
            except Subject.DoesNotExist:
                faculty_obj, fac_cr = Department.objects.get_or_create(name=class_details['faculty'])
                if fac_cr:
                    logger.info("created faculty %s" % class_details['faculty'])
                subject_obj = Subject(code=class_details['subject'], name=class_details['subject'], faculty=faculty_obj)
                subject_obj.save()
                logger.info("created subject %s" % class_details['subject'])
            class_obj = SchoolClass(code=class_code, name=class_code, subject=subject_obj, cycle=current_cycle, teacher=teacher)
            class_obj.save()
            logger.info("created class %s in cycle %s" % (class_details['subject'], current_cycle))

        # remove students not in list
        for student in class_obj.students.all():
            if not student.timetable_id in class_details['students']:
                Enrolment.objects.get(student=student, school_class=class_obj).delete()
                logger.info("Removing student %s from class %s" % (student, class_obj))

        # add students in list
        for student_code in class_details['students']:
            try:
                student_obj = Student.objects.get(timetable_id=student_code)
            except Student.DoesNotExist:
                logger.warn("Could not find student %s; not adding to class %s" % (student_code, class_obj))
                continue
            Enrolment.objects.get_or_create(student=student_obj, school_class=class_obj)

    # create timetable entries in DB
    # TODO - what to do with existing TT in DB? Delete all entries for classes? Check each class?
    for tt_entry in tt_entries:
        try:
            room = Location.objects.get(code=tt_entry[2])
        except Location.DoesNotExist:
            room = Location(code=tt_entry[2], description=tt_entry[2])
            room.save()
            logger.info("Created location %s" % (tt_entry[2]))
        try:
            d = Day.objects.get(code=tt_entry[0])
            p = Period.objects.get(code=tt_entry[1], periodset=d.periodset)
            try:
                ent = Entry.objects.get(day=d, period=p, location=room,
                                        school_class=SchoolClass.objects.get(code=tt_entry[3]))
            except Entry.DoesNotExist:
                ent = Entry(day=d, period=p, location=room, school_class=SchoolClass.objects.get(code=tt_entry[3]))
                logger.info("created timetable entry %s" % (ent))
            ent.save()  # call save which will trigger updating of google cal

        except (Day.DoesNotExist, Period.DoesNotExist, SchoolClass.DoesNotExist) as e:
            logger.warn("Could not create timetable entry for %s %s %s %s - %s" % (tt_entry[0], tt_entry[1],
                                                                                   tt_entry[2], tt_entry[3], e))
            continue


def import_authcate_from_ldap():
    import ldap
    server = 'ldap://ldap.somewhere.edu'
    base_dn = 'REPLACE_WITH_BASE_DN'
    username = 'REPLACE_WITH_DN_OF_USER_FOR_LOGIN'
    password = 'XXX'
    directory = ldap.initialize(server)
    directory.simple_bind_s(username, password)
    for s in Student.objects.all():
        filt = "(employeenumber=J%s)" % s.timetable_id.upper()
        results = directory.search_s(base_dn, ldap.SCOPE_SUBTREE, filt)
        try:
            s.network_id = results[0][1]['uid'][0]
            logger.info("setting user %s network id to %s" % (s, s.network_id))
            s.save()
        except (IndexError, KeyError):
            logger.info("could not obtain network id for user %s" % (s))
            pass

    for t in StaffMember.objects.all():
        filt = "(mail=%s)" % t.email
        results = directory.search_s(base_dn, ldap.SCOPE_SUBTREE, filt)
        try:
            t.network_id = results[0][1]['uid'][0]
            logger.info("setting user %s network id to %s" % (t, t.network_id))
            t.save()
        except (IndexError, KeyError):
            logger.info("could not obtain network id for user %s" % (t))
            pass

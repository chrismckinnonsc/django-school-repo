from school.models import *
import csv
import tempfile
import logging
logger = logging.getLogger(__name__)


def export_mds_to(OutFile):
    writer = csv.writer(OutFile, lineterminator='\n')
    writer.writerow(["Student ID Number","VTAC Number","Course Code","Family Name","Given Names","Preferred Name",
                     "Title","Date of Birth","Gender","Expiry Date","House or unit number","Street Address","Suburb",
                     "State","Postcode","Home telephone number","Mobile telephone number",
                     "Acceptable Use Policy Accepted","Internet Access Permitted"])
    students = Student.objects.all()
    for s in students:
        #TODO - Fix AUP and Internet Access items
        try:
            enddate = s.start_date.replace(s.start_date.year + 3).strftime("%Y%m%d") #TODO - fudged until can find real enddate solution
        except AttributeError:
            logger.error("Error determining end date for student %s" % s)
            enddate = "20131231"
        if s.is_current:
            (house_no, street_add) = s.address2.split(" ", 1)
            writer.writerow([s.timetable_id, s.uni_application_code, "", s.last_name, s.first_name, s.preferred_name, s.title,
                             s.date_of_birth.strftime("%Y%m%d"), s.gender, enddate,
                             house_no, street_add, s.address3, s.state, s.post_code, s.home_number,
                             s.mobile_number,"1","1"])

def export_mds():
    mdsfile = tempfile.NamedTemporaryFile(suffix='.csv',delete=False)
    export_mds_to(mdsfile)
    #if platform=windows
    #if pscp exists
    #set cmd to pscp path
    #else
    #if scp exists
    #set cmd to scp path
    #if cmd set
    #run cmd to copy file across
    #TODO - auth key?
    #else
    #raise exception

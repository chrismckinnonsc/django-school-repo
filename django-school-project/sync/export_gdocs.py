import gspread
from school.models import *

def update_students_sheet():
    #TODO - use OAuth instead
    gc = gspread.login("REPLACE_GOOGLE_USERNAME", "REPLACE_GOOGLE_PASSWORD")

    #student-test spreadsheet - TODO should allow for choice of destination?
    ss = gc.open_by_key('REPLACE_WITH_SPREADSHEET_KEY')
    ss.del_worksheet(0)
    ws = ss.add_worksheet(title="Students", rows="0", cols="10")
    ws.append_row(["CASES ID", "email", "First Name", "Pref Name", "Last Name", "Authcate ID", "Year Level",
                   "House", "Mentor", "VSN"])
    for s in Student.objects.filter(is_current=True):
        ws.append_row([s.timetable_id, s.email, s.first_name, s.preferred_name, s.last_name, s.network_id,
                       s.year_level, s.house_group, s.mentor_group, s.govt_student_code])


def update_class_sheets():
    for cl in SchoolClass.objects.filter(cycle=Semester.working()):
        #get sheet corresponding to class
        #if no match, create new sheet - ??? Teacher ???
        #delete all data on sheet
        #for s in cl.students.filter(is_current=True):
            #add student details to sheet (email, ID, first, preferred, last names, year, house, mentor group, mentor)
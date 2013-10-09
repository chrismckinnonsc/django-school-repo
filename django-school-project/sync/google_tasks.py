from school.models import Subject, SchoolClass, Student, StaffMember, Semester

import httplib2

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import SignedJwtAssertionCredentials
import hashlib
import json
import random
import string
import datetime
import time
import copy

import celery

import logging
logger = logging.getLogger(__name__)

from django.conf import settings

#TODO - create spreadsheets of classes
#TODO - implement week A and week B as per http://mrcaffrey.wordpress.com/2013/07/24/labelling-teaching-weeks-in-google-calendar


# extra scopes have to be added to the APIs console https://code.google.com/apis/console/b/0
# and https://admin.google.com/YOUR_DOMAIN/ManageOauthClients
SCOPES_DIR = [
      'https://www.googleapis.com/auth/apps.groups.settings',
      'https://www.googleapis.com/auth/admin.directory.user',
      'https://www.googleapis.com/auth/admin.directory.orgunit',
      'https://www.googleapis.com/auth/admin.directory.group',
      'https://www.googleapis.com/auth/admin.directory.group.member',
      ]
SCOPES_CAL = [
      'https://www.googleapis.com/auth/calendar',
      ]
SCOPES_PLUS = [
      'https://www.googleapis.com/auth/plus.me',
      'https://www.googleapis.com/auth/plus.stream.write',
      'https://www.googleapis.com/auth/plus.circles.read',
      'https://www.googleapis.com/auth/plus.circles.write',
    ]
SCOPES = SCOPES_DIR + SCOPES_CAL + SCOPES_PLUS


#@celery.task(name='google_task')
class GoogleTask(celery.Task):
    dir_service = None
    settings_service = None
    calendars = None
    plus = None

    def setup_plus(self):
        if self.plus is None:
            logger.debug('building Plus service')
            http_plus = self.key_auth("REPLACE_ADMIN_USER@DOMAIN", scopes=SCOPES_PLUS)
            self.plus = self.build_service('plus', 'v1domains', http_plus)
    
    def setup_cal(self):
        if self.calendars is None:
            logger.debug('building calendar service')
            http_cal = self.key_auth(settings.GOOGLE_CAL_USER, scopes=SCOPES_CAL)
            self.calendars = self.build_service('calendar', 'v3', http_cal)

    def setup_dir(self):
        if self.dir_service is None:
            logger.debug('building dir service')
            http_dir = self.key_auth(settings.GOOGLE_DIR_USER, scopes=SCOPES_DIR)
            self.dir_service = self.build_service('admin', 'directory_v1', http=http_dir)
            self.groups = self.dir_service.groups()
            self.members = self.dir_service.members()
            self.users = self.dir_service.users()

        if self.settings_service is None:
            logger.debug('building groups settings service')
            self.settings_service = self.build_service('groupssettings', 'v1', http=http_dir)
            self.groupssettings = self.settings_service.groups()

    def run(self, operation, **kwargs):
        try:
            if operation == 'google_update_group':
                self.setup_dir()
                self.google_update_group(kwargs['group_email'], kwargs['group_name'], kwargs['new_members'],
                                         kwargs.get('new_owners', False), kwargs.get('group_settings', None))
            elif operation == 'google_update_user':
                self.setup_dir()
                self.google_update_user(kwargs['user'], kwargs.get('OU', False))
            elif operation == 'google_create_cal':
                self.setup_cal()
                self.google_create_cal(kwargs['cal_name'], kwargs.get('owners', []), kwargs.get('description', ''),
                                       kwargs.get('timezone', settings.TIME_ZONE))
            elif operation == 'google_create_cal_from_class':
                self.setup_cal()
                self.google_create_cal(kwargs['schoolclass'])
            elif operation == 'google_update_event':
                self.setup_cal()
                self.google_update_event(kwargs['calendar_id'], kwargs['event_id'], kwargs.get('title', None),
                                         kwargs.get('start', None), kwargs.get('end', None), 
                                         kwargs.get('attendees', None), kwargs.get('location', None))
            elif operation == 'google_create_event':
                self.setup_cal()
                self.google_create_event(kwargs['calendar_id'], kwargs['title'], kwargs['start'], kwargs['end'],
                                         kwargs['attendees'], kwargs.get('location',''))
            elif operation == 'google_update_timetable_event':
                self.setup_cal()
                self.google_update_timetable_event(kwargs['tt_event'], kwargs.get('date_obj', None))
            else:
                logging.warn('invalid operation %s' % operation)
        except KeyError as e:
            logger.error("required parameter %s not specified for operation %s" % (e, operation))

    def build_service(self, serviceName, version, http):
        retries = 10
        for n in range(1, retries+1):
            try:
                return build(serviceName, version, http=http)
            except AccessTokenRefreshError, e:
                if n < retries:
                    wait_on_fail = (2 ** n) if (2 ** n) < 60 else 60
                    randomness = float(random.randint(1,1000)) / 1000
                    wait_on_fail += randomness
                    if n > 3:
                        logger.warn('AccessTokenRefreshError. Retrying in %s seconds...' % (int(wait_on_fail)))
                    time.sleep(wait_on_fail)
                    if n > 3:
                        logger.warn('attempt %s/%s' % (n+1, retries))
                    continue
                else:
                    logger.error('AccessTokenRefreshError')
                    raise

    def key_auth(self, user_email, scopes=SCOPES, http=None):
        """
         This sets up auth using a private key set up as per: https://developers.google.com/drive/delegation
         This is probably preferable to google_auth as it is tied to a service account rather than a person, and can
         impersonate other users
        """
        f = file(settings.GOOGLE_SERVICE_ACCOUNT_PKCS12_FILE_PATH, 'rb')
        key = f.read()
        f.close()
        credentials = SignedJwtAssertionCredentials(settings.GOOGLE_SERVICE_ACCOUNT_EMAIL, key,
                                                    scope=scopes, sub=user_email)
        if not http:
            http = httplib2.Http()
        http = credentials.authorize(http)
        return http

    #TODO - need to catch 401 errors, see if it's an auth problem, and attempt a re-auth
    def execute(self, command):
        retries = 10
        for n in range(1, retries+1):
            try:
                result = command.execute()
                return result
            except HttpError, e:
                error = json.loads(e.content)
                try:
                    reason = error['error']['errors'][0]['reason']
                    http_status = error['error']['code']
                    message = error['error']['errors'][0]['message']
                    if reason == 'notFound': # Object not found; return None
                        return None
                    if n < retries and reason in ['rateLimitExceeded', 'userRateLimitExceeded', 'backendError']:
                        wait_on_fail = (2 ** n) if (2 ** n) < 60 else 60
                        randomness = float(random.randint(1,1000)) / 1000
                        wait_on_fail += randomness
                        if n > 3:
                            logger.warn('Temporary error %s. Backing off %s seconds...' % (reason, int(wait_on_fail)))
                        time.sleep(wait_on_fail)
                        if n > 3:
                            logger.warn('attempt %s/%s\n' % (n+1, retries))
                        continue
                    logger.error('Error %s: %s - %s' % (http_status, message, reason))
                    raise
                except KeyError:
                    logger.error('Unknown Error: %s' % e)
                    raise
            except AccessTokenRefreshError, e: #TODO - redirect to auth
                logger.error('Error: Authentication Token Error - %s' % e)
                raise

    def google_update_group(self, group_email, group_name, new_members, new_owners=False, group_settings=None):
        #TODO - use fields parameter in API calls to improve performance https://developers.google.com/admin-sdk/directory/v1/guides/performance
        #TODO - save google ID in the database
        #TODO - catch exceptions!
        existing_members = []
        existing_owners = []
    
        added_members = []
        added_owners = []
        removed_members = []
        removed_owners = []
    
        #grab current membership
        current_page = self.execute(self.members.list(groupKey=group_email))
        all_members = copy.deepcopy(current_page)
        while current_page and 'nextPageToken' in current_page:
            current_page = self.execute(self.members.list(groupKey=group_email, pageToken=current_page['nextPageToken']))
            if current_page and 'members' in current_page:
                all_members['members'].extend(current_page['members'])
    
        if all_members:
            if 'members' in all_members: #groups which exist without members don't have a members key
                for m in all_members['members']:
                    try:
                        if m['role'] == 'OWNER':
                            existing_owners.append(m['email'].lower())
                        else:
                            existing_members.append(m['email'].lower())
                    except KeyError:
                        pass
        else:
            logger.info("group %s does not exist" % group_name)
            body={
                "kind": "admin#directory#group",
                "email": group_email,
                "name": group_name,
                "description": "Generated on %s by %s" % (time.asctime(), settings.PROJECT_NAME ),
            }
            self.execute(self.groups.insert(body=body))
            #TODO check for exceptions
        for member in existing_members:
            if not ((new_members and new_members.filter(email__iexact=member).exists()) or (new_owners and new_owners.filter(email__iexact=member).exists())):
                #TODO - alert, but don't remove non-domain members
                #TODO - catch members who no longer exist as users
                if self.execute(self.members.delete(groupKey=group_email, memberKey=member)) == None:
                    logger.error("Error deleting %s from %s: could not find membership" % (member, group_email))
                    continue
                logger.info("removed member %s from %s" % (member, group_name))
                removed_members.append(member)
        if new_owners:
            for owner in existing_owners:
                if not new_owners.filter(email__iexact=owner).exists():
                    if self.execute(self.members.delete(groupKey=group_email, memberKey=owner)) == None:
                        logger.error("Error deleting %s from %s: could not find membership" % (owner, group_email))
                        continue
                    logger.info("removed owner %s from %s" % (owner, group_name))
                    removed_owners.append(owner)
    
        if new_members:
            for new_member in new_members.distinct():
                if new_member.email:
                    if not new_member.email.lower() in existing_members:
                        body={"kind": "admin#directory#member", "email": new_member.email, "role": "MEMBER", "type": "USER"}
                        if not self.execute(self.members.insert(groupKey=group_email, body=body)):
                            logger.error("Could not find group %s" % group_email)
                            continue
                        logger.info("added member %s to %s" % (new_member, group_name))
                        added_members.append(new_member)
                    else:
                        logger.info("skipping %s for %s - already a member" % (new_member, group_name))
                else:
                    logger.info("skipping %s for %s - no email address" % (new_member, group_name))
        if new_owners:
            for new_owner in new_owners.distinct():
                if new_owner.email:
                    if new_owner.email.lower() in existing_members:  # currently only set as member; need to elevate
                        body={"role": "OWNER"}
                        if not self.execute(self.members.update(groupKey=group_email, memberKey=new_owner.email, body=body)):
                            logger.error("Could not find group %s" % group_email)
                            continue
                        logger.info("member %s changed to owner for %s" % (new_owner, group_name))
                        added_owners.append(new_owner)
                    elif not new_owner.email.lower() in existing_owners:
                        body={"kind": "admin#directory#member", "email": new_owner.email, "role": "OWNER", "type": "USER"}
                        if not self.execute(self.members.insert(groupKey=group_email, body=body)):
                            logger.error("Could not find group %s" % group_email)
                            continue
                        logger.info("added owner %s to %s" % (new_owner, group_name))
                        added_owners.append(new_owner)
                    else:
                        logger.info("skipping %s for %s - already an owner" % (new_owner, group_name))
                else:
                    logger.info("skipping %s for %s - no email address" % (new_owner, group_name))
    #                if not new_owner.email.lower() in existing_members: #owners need to be members too...
    #                    body={"kind": "admin#directory#member", "email": new_owner.email, "role": "MEMBER", "type": "USER"}
    #                    if not self.execute(self.members.insert(groupKey=group_email, body=body)):
    #                        logger.error("Could not find group %s" % group_email)
    #                        continue
    #                    logger.info("added member %s to %s" % (new_owner, group_name))
    #                    added_members.append(new_owner)
    #                else:
    #                    logger.info("skipping %s for %s - already a member" % (new_owner, group_name))
    
        #set group settings to allow all in domain to post using groupsettings API
        settings_body = {
                          'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                          'whoCanViewGroup': 'ALL_IN_DOMAIN_CAN_VIEW',
                          'whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                          'allowExternalMembers': 'true',
                          'whoCanPostMessage': 'ALL_IN_DOMAIN_CAN_POST',
                          'allowWebPosting': 'true',
                          'isArchived': 'true',
                          'messageModerationLevel': 'MODERATE_NON_MEMBERS',
                          'showInGroupDirectory': 'true',
                          'includeInGlobalAddressList': 'true',
                        }
        if group_settings:
            settings_body.update(group_settings) #any settings argument passed in will override/augment defaults
        if not self.execute(self.groupssettings.patch(groupUniqueId=group_email, body=settings_body)):
            logger.error("Could not set group settings for %s" % group_email)

    def google_update_user(self, user, OU=False):
        if user.google_id:
            user_google = self.execute(self.users.get(userKey=user.google_id))
        else:
            user_google = self.execute(self.users.get(userKey=user.email))
            if user_google:
                user.google_id = user_google['id']
                user.last_google_update = datetime.datetime.now()
                user.save()
        if user_google:
            user_patch = {'name': {}}
            if user.is_current:
                user_patch['name']['givenName'] = user.preferred_name or user.first_name
                user_patch['name']['familyName'] = user.last_name
                if OU:
                    user_patch['orgUnitPath'] = OU
                #TODO - set photo
            #TODO - below code will suspend non-current users; need to enable at some point
            else:
                user_google['suspended'] = True
            self.execute(self.users.patch(userKey=user.email, body=user_google))
            logger.info("modified google user %s", user.timetable_id)
        else:
            if user.is_current:
                if not user.initial_password or user.initial_password == user.timetable_id:
                    user.initial_password = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(8))
                    user.save()
                user_body = {
                    "name": {
                        "familyName": user.last_name,
                        "givenName": user.preferred_name or user.first_name
                    },
                    "password": hashlib.sha1(user.initial_password).hexdigest(),
                    "hashFunction": "SHA-1",
                    "changePasswordAtNextLogin": True,
                    "primaryEmail": user.email
                }
                if OU:
                    user_body['orgUnitPath'] = OU
    
                #TODO - set photo
                user_google = self.execute(self.users.insert(body=user_body))
                if user_google:
                    user.google_id = user_google['id']
                    user.last_google_update = datetime.datetime.now()
                    user.save()
                    logger.info("created google account for %s", user.timetable_id)
    
                else:
                    logger.error("Error creating Google account for %s" % user)

    def google_create_cal(self, name, owners=[], description='', timezone=settings.TIME_ZONE):
        #TODO - replace with default Timezone
        #TODO - need to save created cal ID to DB
        cal_body = {'summary': name, 'description': description, 'timeZone': timezone}
        cal = self.execute(self.calendars.calendars().insert(body=cal_body))
        logger.info("created calendar %s %s" % (name, cal['id']))
        acl = self.execute(self.calendars.acl().list(calendarId=cal['id']))
        for rule in acl['items']:
            if rule['scope']['type'] == 'user' and rule['role'] == 'owner' and rule['scope']['value'] != cal['id']:
                self.execute(self.calendars.acl().delete(calendarId=cal['id'], ruleId=rule['id']))
        for owner in owners:
            newowneracl = {'role': 'owner', 'scope': {'type': 'user', 'value': owner}}
            self.execute(self.calendars.acl().insert(calendarId=cal['id'], body=newowneracl))
            logger.info("added user %s to calendar %s" % (owner, name))
        return cal

    def google_create_cal_from_class(self, schoolclass):
        cal = self.google_create_cal("%s-%s" % (schoolclass.code, schoolclass.cycle.year),
                               description="%s %s" % (schoolclass.code, schoolclass.cycle.year))
        schoolclass.google_calendar_id = cal['id']
        schoolclass.save()


    def google_update_event(self, calendar_id, event_id, title=None, start=None, end=None, attendees=None,
                            location=None, timezone=settings.TIME_ZONE):
        """start and end need to be isoformat time strings e.g. 2013-06-14T12:00:00.000"""
        event = {}
        if title:
            event['summary'] = title
        if location:
            event['location'] = location
        if start:
            event['start'] = {
                'dateTime': start, #TODO - need to convert to string '2013-06-14T12:00:00.000+10:00'
                'timeZone': timezone,
            }
        if end:
            event['end'] = {
                'dateTime': end, #TODO - need to convert to string '2013-06-14T12:00:00.000+10:00'
                'timeZone': timezone,
            }
        if attendees:
            event['attendees'] = []
            for attendee in attendees:
                event['attendees'].append({'email': attendee, 'responseStatus': 'accepted'})
        return self.execute(self.calendars.events().patch(calendarId=calendar_id, eventId=event_id, body=event))

    def google_create_event(self, calendar_id, title, start, end, attendees, location='', timezone=settings.TIME_ZONE):
        """start and end need to be isoformat time strings e.g. 2013-06-14T12:00:00.000"""
        event = {
            'summary': title,
            'location': location,
            'start': {
                'dateTime': start,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end,
                'timeZone': timezone,
            },
            #'recurrence': [
            #  'RRULE:FREQ=WEEKLY;UNTIL=20130712T020000Z;INTERVAL=2;BYDAY=FR',
            #],
            'attendees': [],
        }
        if attendees:
            for attendee in attendees:
                event['attendees'].append({'email': attendee, 'responseStatus': 'accepted'})
        return self.execute(self.calendars.events().insert(calendarId=calendar_id, body=event))

    #TODO - what to do about date_obj here?????
    def google_update_timetable_event(self, tt_event, date_obj=None):
        if tt_event.google_event_id:
            self.google_update_event(tt_event.entry.school_class.google_calendar_id,
                                     tt_event.google_event_id,
                                     title=tt_event.entry.school_class.name,
                                     start=tt_event.start(date_obj=date_obj).isoformat(),
                                     end=tt_event.end(date_obj=date_obj).isoformat(),
                                     attendees=tt_event.attendees(),
                                     location=tt_event.location().code)
        else:  # create new event
            if not tt_event.entry.school_class.google_calendar_id:
                self.google_create_cal_from_class(tt_event.entry.school_class)
            g = self.google_create_event(tt_event.entry.school_class.google_calendar_id,
                                         tt_event.entry.school_class.name,
                                         tt_event.start(date_obj=date_obj).isoformat(),
                                         tt_event.end(date_obj=date_obj).isoformat(),
                                         tt_event.attendees(),
                                         tt_event.location().code)
            tt_event.google_event_id = g['id']
            tt_event.save()



#register with celery
google_task = celery.registry.tasks[GoogleTask.name]


def update_google_groups_all_classes(request=False):
    #TODO - split class/subject from all/year groups
    #TODO - remove old groups
    #TODO - all-staff group,
    #TODO - teaching-staff/ES-staff
    #TODO - faculty groups
    #TODO Mentor groups come from timetable currently - should check if this matches import data

    logger.info("--------- Starting Google Group Sync %s -----------" % time.asctime())

    domain = settings.GOOGLE_APPS_DOMAIN
    year = Semester.working(request).year

    #update all classes in the working cycle
    for cl in SchoolClass.objects.filter(cycle=Semester.working(request)):
        google_task.delay('google_update_group', group_email="%s-%s@%s" % (cl.code, year, domain), group_name=cl.name,
                          new_members=cl.students.filter(is_current=True), 
                          new_owners=StaffMember.objects.filter(schoolclass=cl))

    #update all subjects with classes in the working cycle
    #TODO - update to use .teachers() and .students() methods from subject?
    for sub in Subject.objects.all():
        #get the classes in this subject in the working cycle
        sub_classes = SchoolClass.objects.filter(subject=sub).filter(cycle=Semester.working(request))
        google_task.delay('google_update_group', group_email="%s-%s@%s" % (sub.code, year, domain), group_name=sub.name,
                        new_members=Student.objects.filter(is_current=True).filter(schoolclass__in=sub_classes),
                        new_owners=StaffMember.objects.filter(is_current=True).filter(schoolclass__in=sub_classes))

    #update all students group
    google_task.delay('google_update_group', group_email="students@%s" % domain, group_name="Students",
                    new_members=Student.objects.filter(is_current=True), 
                    group_settings={'messageModerationLevel': 'MODERATE_ALL_MESSAGES'})

    #update year level groups
    for yearlevel in ["10", "11", "12"]:
        google_task.delay('google_update_group', group_email="year%s-%s@%s" % (yearlevel, year, domain), 
                          group_name="Year %s %s" % (yearlevel, year),
                          new_members=Student.objects.filter(is_current=True, year_level=yearlevel),
                          group_settings={'messageModerationLevel': 'MODERATE_ALL_MESSAGES'})
    #update house groups
    for house in list(set(Student.objects.filter(is_current=True).values_list('house_group', flat=True))):
        if not house:
            continue
        google_task.delay('google_update_group', group_email="%s-House@%s" % (house.capitalize(), domain), 
                          group_name="%s House" % house.capitalize(),
                          new_members=Student.objects.filter(house_group=house).filter(is_current=True),
                          new_owners=StaffMember.objects.filter(house_group=house).filter(is_current=True),
                          group_settings={'messageModerationLevel': 'MODERATE_ALL_MESSAGES'})
        google_task.delay('google_update_group', group_email="%s-Staff@%s" % (house.capitalize(), domain), 
                          group_name="%s Staff" % house.capitalize(), new_members=False, 
                          new_owners=StaffMember.objects.filter(house_group=house).filter(is_current=True))
        google_task.delay('google_update_group', group_email="%s-Mentors@%s" % (house.capitalize(), domain), 
                          group_name="%s Mentors" % house.capitalize(), new_members=False, 
                          new_owners=StaffMember.objects.filter(house_group=house).filter(schoolclass__code__startswith="MENT"))

    #group for all mentors
    google_task.delay('google_update_group', group_email="Mentors@%s" % domain, group_name="Mentors", new_members=False, 
                      new_owners=StaffMember.objects.filter(schoolclass__code__startswith="MENT"))


def update_google_student(user):
    OU=False
    if user.is_current:
        if user.student_type == 'EXC':
            OU = settings.GOOGLE_STUDENT_OU_EXCH
        elif user.student_type == 'STU':
            OU = settings.GOOGLE_STUDENT_OU
    else:
        OU = settings.GOOGLE_STUDENT_OU_EXIT
    google_task.delay('google_update_user', user=user, OU=OU)


def update_google_staff(user):
    if user.is_current:
        OU = settings.GOOGLE_STAFF_OU
    else:
        OU = settings.GOOGLE_STAFF_OU_EXIT
    google_task.delay('gooogle_update_user', user=user, OU=OU)


def update_google_students_all():
    for stu in Student.objects.filter(timetable_id="XXX9998"):
        update_google_student(stu)



#Not sure if we need this
#def get_calendar(self, id):
#    return self.execute(self.calendars.calendars().get(calendarId=id))




##Some example calendar code
# def cals(self):
#     #create calendar
#     self.build_cal()
#     cal_body = {'summary':'New Calendar Name'}
#     cal = self.execute(self.calendars.calendars().insert(body=cal_body))
#
#     #create event
#     event = {
#       'summary': 'Appointment',
#       'location': 'Somewhere',
#       'start': {
#         'dateTime': '2013-06-14T12:00:00.000+10:00'
#       },
#       'end': {
#         'dateTime': '2013-06-14T12:25:00.000+10:00'
#       },
#       #'recurrence': [
#       #  'RRULE:FREQ=WEEKLY;UNTIL=20130712T020000Z;INTERVAL=2;BYDAY=FR',
#       #],
#       'attendees': [
#         {
#           'email': 'sample_email@domain.com',
#           'responseStatus': 'accepted',
#         },
#         #can add all attendees here
#         {
#           'email': 'another_email@somewhere.com',
#           'responseStatus': 'accepted',
#         },
#       ],
#     }
#     g_event = self.execute(self.calendars.events().insert(calendarId=cal['id'], body=event))
#
#     #Modify the last event
#     mod_event = {
#       'start': {
#         'dateTime': '2013-06-13T14:00:00.000+10:00'
#       },
#       'end': {
#         'dateTime': '2013-06-13T14:25:00.000+10:00'
#       },
#     }
#     g_event2 = self.execute(self.calendars.events().patch(calendarId=cal['id'], eventId=g_event['id'], body=mod_event))
#
#     #add a new owner to the calendar
#     newowneracl = {'role': 'owner', 'scope': {'type': 'user', 'value':'SOME_USER@DOMAIN'}}
#     self.execute(self.calendars.acl().insert(calendarId=cal['id'], body=newowneracl))
#
#     #remove an owner
#     self.execute(self.calendars.acl().delete(calendarId=cal['id'],ruleId='user:OWNER_EMAIL@ADDRESS.com'))
#

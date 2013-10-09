################################################################################################
# DEPRECATED - use google_tasks.py instead
################################################################################################


from school.models import Subject, SchoolClass, Student, StaffMember, Semester

import httplib2

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import SignedJwtAssertionCredentials
from django.contrib.sessions.backends.db import SessionStore
import hashlib
import json
import random
import string
import datetime
import copy
import urlparse

from djcelery import celery

from django.conf import settings
import logging,time
logger = logging.getLogger(__name__)

# extra scopes have to be added to the APIs console https://code.google.com/apis/console/b/0
# and https://admin.google.com/YOURDOMAIN/ManageOauthClients
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

@celery.task
def add(x, y):
    return x + y

#TODO - create spreadsheets of classes

class GoogleSync():
    @classmethod
    def get_or_create(cls):
        s = SessionStore()
        try:
            return s['google_sync']
        except KeyError:
            google_sync = cls()
            s['google_sync'] = google_sync
            s.save()
            return google_sync
    #XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    #TODO - save the session ID somewhere and save the session when changes are made to the google_sync object
    #XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    def __init__(self, request=None):
        s = SessionStore()
        if not 'google_sync' in s:
            s['google_sync'] = self
            s.save()

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

    def build_dir(self):
        if not hasattr(self, 'dir_service'):
            logger.debug('building dir service')
            http_dir = self.key_auth(settings.GOOGLE_DIR_USER, scopes=SCOPES_DIR)
            self.dir_service = self.build_service('admin', 'directory_v1', http=http_dir)
            self.groups = self.dir_service.groups()
            self.members = self.dir_service.members()
            self.users = self.dir_service.users()
        if not hasattr(self, 'settings_service'):
            logger.debug('building groups settings service')
            http_dir = self.key_auth(settings.GOOGLE_DIR_USER, scopes=SCOPES_DIR)
            self.settings_service = self.build_service('groupssettings', 'v1', http=http_dir)
            self.groupssettings = self.settings_service.groups()


    def build_cal(self):
        if not hasattr(self, 'calendars'):
            logger.debug('building calendar service')
            http_cal = self.key_auth(settings.GOOGLE_CAL_USER, scopes=SCOPES_CAL)
            self.calendars = self.build_service('calendar', 'v3', http_cal)

    def build_plus(self):
        if not hasattr(self, 'plus'):
            logger.debug('building Plus service')
            http_plus = self.key_auth("REPLACE_ADMIN_USER@DOMAIN", scopes=SCOPES_PLUS)
            self.plus = self.build_service('plus', 'v1domains', http_plus)

    # def google_auth(self, http=None, request=None):
    #     # need to have client secrets JSON file created and downloaded from http://code.google.com/apis/console
    #     storage = Storage(settings.GOOGLE_CLIENT_STORAGE)
    #     credentials = storage.get()
    #
    #     if credentials is None or credentials.invalid:
    #         if request:
    #             #TODO - handle authorization and callback
    #             pass
    #         else:
    #             #TODO - error out
    #             pass
    #
    #     # Create an httplib2.Http object to handle our HTTP requests and authorize it
    #     # with our good Credentials.
    #     if not http:
    #         http = httplib2.Http()
    #     http = credentials.authorize(http)
    #     return http

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

    #TODO - use async task of some sort (celery?)
    #TODO - use fields parameter in API calls to improve performance https://developers.google.com/admin-sdk/directory/v1/guides/performance
    #TODO - save google ID in the database
    #TODO - catch exceptions!
    def sync_group(self, group_email, group_name, new_members, new_owners=False, group_settings=None):
        self.build_dir()
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
                    if not new_owner.email.lower() in existing_owners:
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


    def update_google_groups(self, request):
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
            self.sync_group("%s-%s@%s" % (cl.code, year, domain), cl.name,
                            cl.students.filter(is_current=True), StaffMember.objects.filter(schoolclass=cl))
        
        #update all subjects with classes in the working cycle
        #TODO - update to use .teachers() and .students() methods from subject?
        for sub in Subject.objects.all():
            #get the classes in this subject in the working cycle
            sub_classes = SchoolClass.objects.filter(subject=sub).filter(cycle=Semester.working(request))
            self.sync_group("%s-%s@%s" % (sub.code, year, domain), sub.name,
                            Student.objects.filter(is_current=True).filter(schoolclass__in=sub_classes),
                            StaffMember.objects.filter(is_current=True).filter(schoolclass__in=sub_classes))
        
        #update all students group
        self.sync_group("students@%s" % domain, "Students",
                        Student.objects.filter(is_current=True), group_settings={'messageModerationLevel': 'MODERATE_ALL_MESSAGES'})

        #update year level groups
        for yearlevel in ["10", "11", "12"]:
            self.sync_group("year%s-%s@%s" % (yearlevel, year, domain), "Year %s %s" % (yearlevel, year),
                            Student.objects.filter(is_current=True, year_level=yearlevel), False,
                            group_settings={'messageModerationLevel': 'MODERATE_ALL_MESSAGES'})
        #update house groups
        for house in list(set(Student.objects.filter(is_current=True).values_list('house_group', flat=True))):
            self.sync_group("%s-House@%s" % (house.capitalize(), domain), "%s House" % house.capitalize(),
                            Student.objects.filter(house_group=house).filter(is_current=True),
                            StaffMember.objects.filter(house_group=house).filter(is_current=True),
                            group_settings={'messageModerationLevel': 'MODERATE_ALL_MESSAGES'})
            self.sync_group("%s-Staff@%s" % (house.capitalize(), domain), "%s Staff" % house.capitalize(),
                            False, StaffMember.objects.filter(house_group=house).filter(is_current=True))
            self.sync_group("%s-Mentors@%s" % (house.capitalize(), domain), "%s Mentors" % house.capitalize(),
                            False, StaffMember.objects.filter(house_group=house).filter(schoolclass__code__startswith="MENT"))
        
        #group for all mentors
        self.sync_group("Mentors@%s" % domain, "Mentors", False, StaffMember.objects.filter(schoolclass__code__startswith="MENT"))

    def update_google_student(self, user):
        OU=False
        if user.is_current:
            if user.student_type == 'EXC':
                OU = settings.GOOGLE_STUDENT_OU_EXCH
            elif user.student_type == 'STU':
                OU = settings.GOOGLE_STUDENT_OU
        else:
            OU = settings.GOOGLE_STUDENT_OU_EXIT
        self.update_google_user(user, OU=OU)

    def update_google_staff(self, user):
        if user.is_current:
            OU = settings.GOOGLE_STAFF_OU
        else:
            OU = settings.GOOGLE_STAFF_OU_EXIT
        self.update_google_user(user, OU=OU)

    def update_google_user(self, user, OU=False):
        self.build_dir()
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


    def update_google_students(self):
        for stu in Student.objects.filter(timetable_id="XXX9998"):
            self.update_google_student(stu)

    def create_calendar(self, name, owners=[], description='', timezone='Australia/Melbourne'):
        self.build_cal()
        cal_body = {'summary': name, 'description': description, 'timeZone': timezone}
        cal = self.execute(self.calendars.calendars().insert(body=cal_body))
        logger.info("created calendar %s" % name)
        acl = self.execute(self.calendars.acl().list(calendarId=cal['id']))
        for rule in acl['items']:
            if rule['scope']['type'] == 'user' and rule['role'] == 'owner' and rule['scope']['value'] != cal['id']:
                self.execute(self.calendars.acl().delete(calendarId=cal['id'], ruleId=rule['id']))
        for owner in owners:
            newowneracl = {'role': 'owner', 'scope': {'type': 'user', 'value': owner}}
            self.execute(self.calendars.acl().insert(calendarId=cal['id'], body=newowneracl))
            logger.info("added user %s to calendar %s" % (owner, name))
        return cal

    def get_calendar(self, id):
        self.build_cal()
        return self.execute(self.calendars.calendars().get(calendarId=id))

    def update_event(self, calendar_id, event_id, title=None, start=None, end=None, attendees=None, location=None):
        self.build_cal()
        event = {}
        if title:
            event['summary'] = title
        if location:
            event['location'] = location
        if start:
            event['start'] = { 'dateTime': start } #TODO - need to convert to string '2013-06-14T12:00:00.000+10:00'
        if end:
            event['end'] = { 'dateTime': end }#TODO - need to convert to string '2013-06-14T12:00:00.000+10:00'
        if attendees:
            event['attendees'] = []
            for attendee in attendees:
                event['attendees'].append({'email': attendee, 'responseStatus': 'accepted'})
        return self.execute(self.calendars.events().patch(calendarId=calendar_id, eventId=event_id, body=event))

    def create_event(self, calendar_id, title, start, end, attendees, location=''):
        """start and end need to be isoformat time strings e.g. 2013-06-14T12:00:00.000"""
        self.build_cal()
        logger.debug("%s %s" % (title, attendees))
        event = {
          'summary': title,
          'location': location,
          'start': {
            'dateTime': start,
            'timeZone': 'Australia/Melbourne' #TODO - replace, or use tz info from start/end value
          },
          'end': {
            'dateTime': end,
            'timeZone': 'Australia/Melbourne' #TODO - replace
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



    #TODO - implement week A and week B as per http://mrcaffrey.wordpress.com/2013/07/24/labelling-teaching-weeks-in-google-calendar
    #TODO - replace execute() calls with self.execute()
    def cals(self):
        #create calendar
        self.build_cal()
        cal_body = {'summary':'New Calendar Name'}
        cal = self.execute(self.calendars.calendars().insert(body=cal_body))

        #create event
        event = {
          'summary': 'Appointment',
          'location': 'Somewhere',
          'start': {
            'dateTime': '2013-06-14T12:00:00.000+10:00'
          },
          'end': {
            'dateTime': '2013-06-14T12:25:00.000+10:00'
          },
          #'recurrence': [
          #  'RRULE:FREQ=WEEKLY;UNTIL=20130712T020000Z;INTERVAL=2;BYDAY=FR',
          #],
          'attendees': [
            {
              'email': 'sample_email@domain.com',
              'responseStatus': 'accepted',
            },
            #can add all attendees here
            {
              'email': 'another_email@somewhere.com',
              'responseStatus': 'accepted',
            },
          ],
        }
        g_event = self.execute(self.calendars.events().insert(calendarId=cal['id'], body=event))

        #Modify the last event
        mod_event = {
          'start': {
            'dateTime': '2013-06-13T14:00:00.000+10:00'
          },
          'end': {
            'dateTime': '2013-06-13T14:25:00.000+10:00'
          },
        }
        g_event2 = self.execute(self.calendars.events().patch(calendarId=cal['id'], eventId=g_event['id'], body=mod_event))

        #add a new owner to the calendar
        newowneracl = {'role': 'owner', 'scope': {'type': 'user', 'value':'SOME_USER@DOMAIN'}}
        self.execute(self.calendars.acl().insert(calendarId=cal['id'], body=newowneracl))

        #remove an owner
        self.execute(self.calendars.acl().delete(calendarId=cal['id'],ruleId='user:OWNER_EMAIL@ADDRESS.com'))
'''
flow = flow_from_clientsecrets(settings.GOOGLE_CLIENT_SECRETS,
                                scope=SCOPES,
                                redirect_uri="http://127.0.0.1:8000/admin/sync/token/") #TODO - remove hardcode to server


def oauth_step_1(request=None, redirect_uri=""):
    if redirect_uri:
        flow.redirect_uri = redirect_uri
    elif request:
        splituri = urlparse.urlsplit(request.build_absolute_uri())
        flow.redirect_uri = urlparse.urlunsplit((splituri.scheme, splituri.netloc, splituri.path, None, None))
    authorize_url = flow.step1_get_authorize_url()
    return HttpResponseRedirect(authorize_url)

def oauth_step_2(code):
    storage = Storage(settings.GOOGLE_CLIENT_STORAGE)
    credentials = flow.step2_exchange(code)
    storage.put(credentials)
    credentials.set_store(storage)
'''


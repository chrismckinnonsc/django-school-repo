#DEPRECATED - only used by export_google, which has been superseded by google_tasks

import sys
import os
import pickle
import platform
import webbrowser
import gdata.gauth
import oauth2client.client
import oauth2client.file
import oauth2client.tools
from oauth2client import xsrfutil
import gdata.auth
import gdata.client
import gdata.apps.service
import gdata.docs.service
import gdata.service

from django.conf import settings
from django.http import HttpResponseRedirect

DOMAIN = settings.GOOGLE_APPS_DOMAIN

def authorize(gdataObject):
    gdataObject.ClientLogin(os.environ["GOOGLE_APPS_USERNAME"], os.environ["GOOGLE_APPS_PASSWORD"])


'''
#TODO can't get OAuth to work; attempt this again after new Google APIs support provisioning

APICONSOLE = 'https://code.google.com/apis/console'
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://apps-apis.google.com/a/feeds/groups/',                      # Groups Provisioning API
    'https://apps-apis.google.com/a/feeds/alias/',                       # Nickname Provisioning API
    'https://apps-apis.google.com/a/feeds/policies/',                    # Organization Provisioning API
    'https://apps-apis.google.com/a/feeds/user/',                        # Users Provisioning API
    'https://apps-apis.google.com/a/feeds/emailsettings/2.0/',           # Email Settings API
    'https://apps-apis.google.com/a/feeds/calendar/resource/',           # Calendar Resource API
    'https://apps-apis.google.com/a/feeds/compliance/audit/',            # Audit API
    'https://apps-apis.google.com/a/feeds/domain/',                      # Admin Settings API
    'https://www.googleapis.com/auth/apps/reporting/audit.readonly',     # Admin Audit API
    'https://www.googleapis.com/auth/apps.groups.settings',              # Group Settings API
    'https://www.google.com/m8/feeds',                                   # Contacts / Profiles API
    'https://www.google.com/calendar/feeds/',                            # Calendar Data API
    'https://www.google.com/hosted/services/v1.0/reports/ReportingData'] # Reporting API
OAUTH2FILENAME = "%s/%s" %(settings.SECRETS_PATH, 'oauth.txt')
KEYSECRETFILENAME = "%s/%s" %(settings.SECRETS_PATH, 'key-and-secret.txt')
OAUTH2JSONFILE = "%s/%s" %(settings.SECRETS_PATH, 'client_secrets.json')
OAUTH2USERAGENT = settings.PROJECT_NAME
MISSING_OAUTHJSONFILE_MESSAGE = """
You must create or download a client secrets json file (%s)
from the Google APIs console <https://code.google.com/apis/console>.
""" % OAUTH2JSONFILE

def get_oauth_token(request):
    if not os.path.isfile(OAUTH2JSONFILE):
        message = MISSING_OAUTHJSONFILE_MESSAGE
        print message
        #try:       #    webbrowser.open(str(APICONSOLE))
        #except Exception, e:
        #    print "Error opening web page"
        #    sys.exit(1)
        #message = 'When %s is created/downloaded press Enter to continue ... ' %(OAUTH2JSONFILE)
        #raw_input(message)
    oauth2_flow = oauth2client.client.flow_from_clientsecrets(OAUTH2JSONFILE,
                                                              scope=SCOPES,
                                                              redirect_uri = request.build_absolute_uri())
                                                              #message=MISSING_OAUTHJSONFILE_MESSAGE)
                                                              #TODO - replace message with redirect_uri and make it work
    storage = oauth2client.file.Storage(OAUTH2FILENAME)
    oauth2_credentials = storage.get()
    if oauth2_credentials is None or oauth2_credentials.invalid:
        oauth2_flow.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        authorize_url = oauth2_flow.step1_get_authorize_url()
        return HttpResponseRedirect(authorize_url)
        #oauth2_credentials = oauth2client.tools.run(oauth2_flow, storage)
    oauth2_token = gdata.gauth.OAuth2Token(
        client_id=oauth2_credentials.client_id,
        client_secret=oauth2_credentials.client_secret,
        scope=SCOPES,
        user_agent=OAUTH2USERAGENT,
        access_token=oauth2_credentials.access_token,
        refresh_token=oauth2_credentials.refresh_token
    )
    return oauth2_token

def get_oauth_token(request, client_key='anonymous', client_secret='anonymous'):
#    apps = gdata.apps.service.AppsService(domain=settings.GOOGLE_APPS_DOMAIN,
#                                              source='%s / Python %s.%s.%s %s / %s %s /' % (settings.PROJECT_NAME,
#                                                                    sys.version_info[0], sys.version_info[1],
#                                                                    sys.version_info[2], sys.version_info[3],
#                                                                    platform.platform(), platform.machine()))
    apps = gdata.docs.service.DocsService(source=settings.PROJECT_NAME)
    if request.GET.get('part2', False):
        #THIS IS THE SECOND PART (after authorisation)
        oauth_token = gdata.auth.OAuthTokenFromUrl(request.build_absolute_uri())
        if oauth_token:
            oauth_token.secret = client_secret
            oauth_token.oauth_input_params = gdata.auth.OAuthInputParams(
                gdata.auth.OAuthSignatureMethod.HMAC_SHA1, client_key, consumer_secret=client_secret)
            apps.SetOAuthToken(oauth_token)
        else:
            print 'No oauth_token found in the URL'

        try:
            final_token = apps.UpgradeToOAuthAccessToken(oauth_token)
        except gdata.service.TokenUpgradeFailed:
            print 'Failed to upgrade the token. Did you grant access?'
            return False #TODO VALUE???
        f = open(OAUTH2FILENAME, 'wb')
        f.write('%s\n' % (settings.GOOGLE_APPS_DOMAIN,))
        pickle.dump(final_token, f)
        f.close()
        return HttpResponseRedirect('/admin/sync/')
    else:
    #THIS IS THE FIRST PART
        fetch_params = {'xoauth_displayname':'Django-School'}
        apps.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1, consumer_key=str(client_key),
                                     consumer_secret=str(client_secret))
        try:
            request_token = apps.FetchOAuthRequestToken(scopes=SCOPES, extra_parameters=fetch_params)
        except gdata.service.FetchingOAuthRequestTokenFailed, e:
            if str(e).find('Timestamp') != -1:
                print "In order to use OAuth, your system time needs to be correct.\nPlease fix your time and try again."
                return False
            else:
                print "Error: %s" % e
                return False
        url_params = {'hd': settings.GOOGLE_APPS_DOMAIN}
        url = apps.GenerateOAuthAuthorizationURL(request_token=request_token, callback_url=request.build_absolute_uri()+'&part2=True',
                                                 extra_params=url_params)
        return HttpResponseRedirect(url)

def authorize(gdataObject):
    oauth_filename = OAUTH2FILENAME
    if os.path.isfile(oauth_filename):
        oauthfile = open(oauth_filename, 'rb')
        domain = oauthfile.readline()[0:-1]
        token = pickle.load(oauthfile)
        oauthfile.close()
        gdataObject.domain = domain
        gdataObject.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1, consumer_key=token.oauth_input_params._consumer.key, consumer_secret=token.oauth_input_params._consumer.secret)
        token.oauth_input_params = gdataObject._oauth_input_params
        gdataObject.SetOAuthToken(token)
        return gdataObject
    else:
        return False
'''

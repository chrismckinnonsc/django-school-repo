from os.path import join, abspath, dirname, realpath, basename
import os

here = lambda *x: realpath(join(abspath(dirname(__file__)), *x))
PROJECT_ROOT = here("..", "..")
root = lambda *x: realpath(join(abspath(PROJECT_ROOT), *x))

PROJECT_NAME = basename(PROJECT_ROOT)

MEDIA_ROOT = root("media")
STATIC_ROOT = root("static")

GOOGLE_APPS_DOMAIN = 'REPLACE_WITH_YOUR_DOMAIN.edu'

AUTH_USER_MODEL = 'school.AuthUser'

SECRETS_PATH = here("..", "secrets")

# email and file path for credentials as per: https://developers.google.com/drive/delegation (see sync/google_tasks.py)
GOOGLE_SERVICE_ACCOUNT_EMAIL = 'REPLACE_ME@developer.gserviceaccount.com'
GOOGLE_SERVICE_ACCOUNT_PKCS12_FILE_PATH = join(SECRETS_PATH, 'REPLACE_ME-privatekey.p12')

GOOGLE_DIR_USER = 'REPLACE_ME@REPLACE_WITH_YOUR_DOMAIN.edu'
GOOGLE_CAL_USER = 'REPLACE_ME@REPLACE_WITH_YOUR_DOMAIN.edu'

GOOGLE_STUDENT_OU = "/Students"
GOOGLE_STAFF_OU = "/Staff"
GOOGLE_STUDENT_OU_EXCH = GOOGLE_STUDENT_OU + "/Exchange Students"
GOOGLE_STUDENT_OU_EXIT = GOOGLE_STUDENT_OU + "/Exited Students"
GOOGLE_STAFF_OU_EXCH = GOOGLE_STAFF_OU + "/Exchange Teachers"
GOOGLE_STAFF_OU_EXIT = GOOGLE_STAFF_OU + "/Exited Staff"
GOOGLE_STAFF_OU_CASUAL = GOOGLE_STAFF_OU + "/Casual\/Sessional"
GOOGLE_STAFF_OU_PRESERVICE = GOOGLE_STAFF_OU + "/Student Teachers"

REALSMART_LEARNER_URI = 'https://data.rlsmart.net/webservices/sims_import_learners_client.php'
REALSMART_MENTOR_URI = 'https://data.rlsmart.net/webservices/sims_import_mentors_client.php'

TIMETABLE_WEEKS = ((1, "A"), (2, "B"))

ADMINS = (
    ("REPLACE with your name", 'REPLACE with your email'),
)

MANAGERS = ADMINS


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Australia/Melbourne'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-au'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# TODO - make sure to set this Environment variable to something random and unique to this host
# https://docs.djangoproject.com/en/dev/howto/deployment/checklist/#secret-key
SECRET_KEY = os.environ["DJANGO_SCHOOL_SECRET_KEY"]

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'django-school-config.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'django-school-config.wsgi.application'


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'south',
    'school',
    'timetable',
    'sync',
    'social_auth',
    'djcelery',

)

# Django-social-auth settings
AUTHENTICATION_BACKENDS = (
    # 'social_auth.backends.twitter.TwitterBackend',
    # 'social_auth.backends.facebook.FacebookBackend',
    # 'social_auth.backends.google.GoogleOAuthBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
    # 'social_auth.backends.google.GoogleBackend',
    # 'social_auth.backends.yahoo.YahooBackend',
    # 'social_auth.backends.browserid.BrowserIDBackend',
    # 'social_auth.backends.contrib.linkedin.LinkedinBackend',
    # 'social_auth.backends.contrib.disqus.DisqusBackend',
    # 'social_auth.backends.contrib.livejournal.LiveJournalBackend',
    # 'social_auth.backends.contrib.orkut.OrkutBackend',
    # 'social_auth.backends.contrib.foursquare.FoursquareBackend',
    # 'social_auth.backends.contrib.github.GithubBackend',
    # 'social_auth.backends.contrib.vk.VKOAuth2Backend',
    # 'social_auth.backends.contrib.live.LiveBackend',
    # 'social_auth.backends.contrib.skyrock.SkyrockBackend',
    # 'social_auth.backends.contrib.yahoo.YahooOAuthBackend',
    # 'social_auth.backends.contrib.readability.ReadabilityBackend',
    # 'social_auth.backends.contrib.fedora.FedoraBackend',
    # 'social_auth.backends.OpenIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_USER_MODEL = 'school.AuthUser'
LOGIN_URL          = '/login-form/'
LOGIN_REDIRECT_URL = '/admin/'
LOGIN_ERROR_URL    = '/login-error/'


# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        #'mail_admins': {
        #    'level': 'ERROR',
        #    'filters': ['require_debug_false'],
        #    'class': 'django.utils.log.AdminEmailHandler'
        #},
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'rotatinglogfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': here("..", "log", "%s.log" % PROJECT_NAME),
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.FileHandler',
            'filename': here("..", "log", "%s.log" % PROJECT_NAME),
            'formatter': 'standard',
        },
        'console':{
            'level':'INFO',
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        # 'django.request': {
        #     'handlers': ['mail_admins'],
        #     'level': 'ERROR',
        #     'propagate': True,
        # },
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'WARN',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django-school-config': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        'sync': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        'school': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        'timetable': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
    },
}

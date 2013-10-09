from .base import *

TEST_RUNNER = "django_nose.NoseTestSuiteRunner"
#TEST_DISCOVER_TOP_LEVEL = PROJECT_ROOT
#TEST_DISCOVER_ROOT = PROJECT_ROOT
#TEST_DISCOVER_PATTERN = "test_*"

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': ':memory:',
#     }
# }

GOOGLE_APPS_DOMAIN = 'REPLACE_WITH_TESTING_DOMAIN.edu'

GOOGLE_STUDENT_OU = "/Test/Students"
GOOGLE_STAFF_OU = "/Test/Staff"
GOOGLE_STUDENT_OU_EXCH = GOOGLE_STUDENT_OU + "/Exchange Students"
GOOGLE_STUDENT_OU_EXIT = GOOGLE_STUDENT_OU + "/Exited Students"
GOOGLE_STAFF_OU_EXCH = GOOGLE_STAFF_OU + "/Exchange Teachers"
GOOGLE_STAFF_OU_EXIT = GOOGLE_STAFF_OU + "/Exited Staff"
GOOGLE_STAFF_OU_CASUAL = GOOGLE_STAFF_OU + "/Casual\/Sessional"
GOOGLE_STAFF_OU_PRESERVICE = GOOGLE_STAFF_OU + "/Student Teachers"


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/media/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    root("sync", "templates"),
)


import os
import sys
import django
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTALLED_APPS = [
    'libyams.orm',
]

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'playground',
#         'USER': 'admin',
#         'PASSWORD': 'pasw',
#         'HOST': 'localhost',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

settings.configure(
    INSTALLED_APPS=INSTALLED_APPS,
    DATABASES=DATABASES,
)

django.setup()

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
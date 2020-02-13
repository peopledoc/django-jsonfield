#!/usr/bin/env python
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.{engine}'.format(
            engine=os.environ.get('DB_ENGINE', 'sqlite3')
         ),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'NAME': os.environ.get('DB_NAME', 'jsonfield'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'jsonfield',
)

SECRET_KEY = '334ebe58-a77d-4321-9d01-a7d2cb8d3eea'

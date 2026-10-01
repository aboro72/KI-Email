"""Isolated SQLite regression configuration, never used by production services."""
from config.settings import *
from django.apps import AppConfig

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MIGRATION_MODULES = {AppConfig.create(entry).label: None for entry in INSTALLED_APPS}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

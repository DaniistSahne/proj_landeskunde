"""
WSGI config for landeskunde_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landeskunde_landeskunde_backend.settings')

application = get_wsgi_application()

GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH', 'C:/Users/daniil/AppData/Local/Programs/OSGeo4W/bin/gdal311.dll')

import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eshop.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app='shop'")
print('Cleared shop migration history')

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bray_project.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute('SELECT id, name, section FROM newapp_menuitem ORDER BY section, name')
rows = cursor.fetchall()

print("Menu Items:")
print("-" * 60)
for r in rows:
    print(f'ID: {r[0]}, Name: {r[1]}, Section: {r[2]}')
print("-" * 60)
print(f"Total items: {len(rows)}")

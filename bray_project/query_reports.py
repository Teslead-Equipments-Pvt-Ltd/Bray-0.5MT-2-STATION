from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT id, name, section FROM newapp_menuitem WHERE LOWER(section) = 'report' ORDER BY name")
rows = cursor.fetchall()
for r in rows:
    print(f'ID: {r[0]}, Name: {r[1]}, Section: {r[2]}')

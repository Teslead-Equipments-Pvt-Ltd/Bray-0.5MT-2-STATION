from django.db import connection

def testmode(mode):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE sync_nonsync_table SET TEST_MODE=%s WHERE ID=1", [mode])
from django.db import connection

def get_abrs_value():
    with connection.cursor() as cursor:
        cursor.execute("""select COL1_VALUE,COL2_VALUE,COL3_VALUE from abrs_value_table""")
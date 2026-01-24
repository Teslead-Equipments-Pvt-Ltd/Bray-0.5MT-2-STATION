from django.db import connection

def get_all_standards():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, STANDARD_ID, STANDARD_NAME, STANDARD_DESC, CREATED_DATE, UPDATED_DATE
            FROM standard
            ORDER BY ID
        """)
        return cursor.fetchall()


def get_next_standard_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(STANDARD_ID), 0) + 1 FROM standard")
        return cursor.fetchone()[0]


def insert_standard(standard_id, name, desc):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO standard (STANDARD_ID, STANDARD_NAME, STANDARD_DESC)
            VALUES (%s, %s, %s)
        """, [standard_id, name, desc])


def update_standard(id, name, desc):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE standard
            SET STANDARD_NAME = %s, STANDARD_DESC = %s
            WHERE ID = %s
        """, [name, desc, id])


def delete_standard_record(id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM standard WHERE ID=%s", [id])


def check_duplicate_name(name, pk=None):
    with connection.cursor() as cursor:
        if pk:
            cursor.execute("SELECT 1 FROM standard WHERE STANDARD_NAME=%s AND ID!=%s", [name, pk])
        else:
            cursor.execute("SELECT 1 FROM standard WHERE STANDARD_NAME=%s", [name])
        return cursor.fetchone()

def delete_multiple_standard_records(ids):
    if not ids:
        return 0

    placeholders = ",".join(["%s"] * len(ids))

    query = f"DELETE FROM standard WHERE id IN ({placeholders})"

    with connection.cursor() as cursor:
        cursor.execute(query, ids)

    return cursor.rowcount  # number of rows deleted


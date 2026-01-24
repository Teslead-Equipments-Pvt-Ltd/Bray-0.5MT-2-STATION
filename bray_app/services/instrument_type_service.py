from django.db import connection


def get_all_instrument_types():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT INSTRUMENT_TYPE_ID, INSTRUMENT_TYPE, INSTRUMENT_STATUS
            FROM instrument_categories
            ORDER BY INSTRUMENT_STATUS DESC, INSTRUMENT_TYPE_ID
        """)
        return cursor.fetchall()


def get_next_instrument_type_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(INSTRUMENT_TYPE_ID), 0) + 1 FROM instrument_categories")
        return cursor.fetchone()[0]


def insert_instrument_type(type_id, name, status):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO instrument_categories
            (INSTRUMENT_TYPE_ID, INSTRUMENT_TYPE, INSTRUMENT_STATUS, CREATED_DATE, UPDATED_DATE)
            VALUES (%s, %s, %s, NOW(), NOW())
        """, [type_id, name, status])


def update_instrument_type(type_id, name, status):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE instrument_categories
            SET INSTRUMENT_TYPE = %s, INSTRUMENT_STATUS = %s, UPDATED_DATE = NOW()
            WHERE INSTRUMENT_TYPE_ID = %s
        """, [name, status, type_id])


def delete_instrument_type_record(type_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM instrument_categories WHERE INSTRUMENT_TYPE_ID=%s", [type_id])


def check_duplicate_name(name, exclude_id=None):
    with connection.cursor() as cursor:
        if exclude_id:
            cursor.execute(
                "SELECT INSTRUMENT_TYPE_ID FROM instrument_categories WHERE LOWER(INSTRUMENT_TYPE)=LOWER(%s) AND INSTRUMENT_TYPE_ID != %s",
                [name, exclude_id]
            )
        else:
            cursor.execute(
                "SELECT INSTRUMENT_TYPE_ID FROM instrument_categories WHERE LOWER(INSTRUMENT_TYPE)=LOWER(%s)",
                [name]
            )
        return cursor.fetchone()

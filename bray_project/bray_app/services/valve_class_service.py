from django.db import connection


def get_all_valve_classes():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, CLASS_ID, CLASS_NAME, CLASS_DESC
            FROM valveclass
            ORDER BY ID
        """)
        return cursor.fetchall()


def get_next_class_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(CLASS_ID), 0) + 1 FROM valveclass")
        return cursor.fetchone()[0]


def insert_valve_class(class_id, name, desc):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO valveclass (CLASS_ID, CLASS_NAME, CLASS_DESC)
            VALUES (%s, %s, %s)
        """, [class_id, name, desc])


def update_valve_class(class_id, new_class_id, name, desc):
    with connection.cursor() as cursor:
        # If class_id is being changed, update it along with other fields
        if class_id != new_class_id:
            cursor.execute("""
                UPDATE valveclass
                SET CLASS_ID = %s, CLASS_NAME = %s, CLASS_DESC = %s
                WHERE CLASS_ID = %s
            """, [new_class_id, name, desc, class_id])
        else:
            cursor.execute("""
                UPDATE valveclass
                SET CLASS_NAME = %s, CLASS_DESC = %s
                WHERE CLASS_ID = %s
            """, [name, desc, class_id])


def delete_valve_class_record(class_id):
    with connection.cursor() as cursor:
        # Set VALVECLASS_ID to NULL in master_pressure_data first
        cursor.execute("""
            UPDATE master_pressure_data
            SET VALVECLASS_ID = NULL
            WHERE VALVECLASS_ID = %s
        """, [class_id])

        # Now delete from valveclass
        cursor.execute("DELETE FROM valveclass WHERE CLASS_ID=%s", [class_id])
    
        


def check_duplicate_name(name, class_id=None):
    with connection.cursor() as cursor:
        if class_id:
            cursor.execute("SELECT 1 FROM valveclass WHERE LOWER(CLASS_NAME)=LOWER(%s) AND CLASS_ID!=%s", [name, class_id])
        else:
            cursor.execute("SELECT 1 FROM valveclass WHERE LOWER(CLASS_NAME)=LOWER(%s)", [name])
        return cursor.fetchone()


def check_duplicate_class_id(class_id, exclude_class_id=None):
    with connection.cursor() as cursor:
        if exclude_class_id:
            cursor.execute("SELECT 1 FROM valveclass WHERE CLASS_ID=%s AND CLASS_ID!=%s", [class_id, exclude_class_id])
        else:
            cursor.execute("SELECT 1 FROM valveclass WHERE CLASS_ID=%s", [class_id])
        return cursor.fetchone()


def delete_multiple_valve_classes(class_ids):
    if not class_ids:
        return 0

    placeholders = ",".join(["%s"] * len(class_ids))
    query = f"DELETE FROM valveclass WHERE CLASS_ID IN ({placeholders})"

    with connection.cursor() as cursor:
        cursor.execute(query, class_ids)
    
    return cursor.rowcount
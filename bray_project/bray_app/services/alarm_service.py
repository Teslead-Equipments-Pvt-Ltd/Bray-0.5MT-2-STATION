from django.db import connection, transaction


def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_all_alarms():
    """Get all alarms."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, ALARM_ID, ALARM_NAME, CREATED_AT, UPDATED_AT
            FROM alarm
            ORDER BY ID
        """)
        rows = cursor.fetchall()
        return [
            {
                'id': r[0],
                'alarm_code': r[1],
                'alarm_name': r[2],
                'created_at': r[3],
                'updated_at': r[4]
            }
            for r in rows
        ]


def get_alarm_by_id(alarm_id):
    """Get a single alarm by ID."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, ALARM_ID, ALARM_NAME, CREATED_AT, UPDATED_AT
            FROM alarm
            WHERE ID = %s
        """, [alarm_id])
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'alarm_code': row[1],
                'alarm_name': row[2],
                'created_at': row[3],
                'updated_at': row[4]
            }
        return None


def create_alarm(alarm_code, alarm_name, alarm_description=None):
    """Create a new alarm."""
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO alarm (ALARM_ID, ALARM_NAME)
            VALUES (%s, %s)
        """, [alarm_code, alarm_name])
        return cursor.lastrowid


def update_alarm(alarm_id, alarm_code, alarm_name, alarm_description=None):
    """Update an existing alarm."""
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE alarm 
            SET ALARM_ID = %s, ALARM_NAME = %s, UPDATED_AT = NOW()
            WHERE ID = %s
        """, [alarm_code, alarm_name, alarm_id])
        return cursor.rowcount > 0


def delete_alarm(alarm_id):
    """Delete an alarm."""
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM alarm WHERE ID = %s", [alarm_id])
        return cursor.rowcount > 0


def check_alarm_code_exists(alarm_code, exclude_id=None):
    """Check if alarm code already exists."""
    with connection.cursor() as cursor:
        if exclude_id:
            cursor.execute("""
                SELECT COUNT(*) FROM alarm 
                WHERE ALARM_ID = %s AND ID != %s
            """, [alarm_code, exclude_id])
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM alarm 
                WHERE ALARM_ID = %s
            """, [alarm_code])
        return cursor.fetchone()[0] > 0


def get_existing_alarm_codes():
    """Get all existing alarm codes."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT ALARM_ID FROM alarm")
        return [row[0] for row in cursor.fetchall()]
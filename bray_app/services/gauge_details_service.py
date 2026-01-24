from django.db import connection
from django.utils import timezone


def get_all_gauges():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                   CAL_DUE_DATE, CAL_DONE_DATE,
                   ACTIVE_STATUS, STATION_ID, DUE_ALARM
            FROM gauge_details
            ORDER BY ACTIVE_STATUS DESC, STATION_ID, INSTRUMENT_ID
        """)
        return cursor.fetchall()


def get_instrument_types():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT INSTRUMENT_TYPE
            FROM instrument_categories
            WHERE INSTRUMENT_STATUS = 'ENABLE'
        """)
        return [row[0] for row in cursor.fetchall()]


def get_next_instrument_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(INSTRUMENT_ID), 0) + 1 FROM gauge_details")
        return cursor.fetchone()[0]


def check_duplicate_serial(serial, exclude_id=None):
    with connection.cursor() as cursor:
        if exclude_id:
            cursor.execute(
                "SELECT INSTRUMENT_ID FROM gauge_details WHERE INSTRUMENT_SER_NO=%s AND INSTRUMENT_ID != %s",
                [serial, exclude_id]
            )
        else:
            cursor.execute(
                "SELECT INSTRUMENT_ID FROM gauge_details WHERE INSTRUMENT_SER_NO=%s",
                [serial]
            )
        return cursor.fetchone()


def insert_gauge(instrument_id, serial, range_val, gauge_type, cal_due_date, cal_done_date, active_status, station_id):
    now_ts = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO gauge_details (
                INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                CAL_DUE_DATE, CAL_DONE_DATE,
                ACTIVE_STATUS, STATION_ID,
                CREATED_DATE, UPDATED_DATE
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [instrument_id, serial, range_val, gauge_type,
              cal_due_date, cal_done_date,
              active_status, station_id,
              now_ts, now_ts])
        
        # Log the insert
        cursor.execute("""
            INSERT INTO gauge_log_details (
                INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                CAL_DUE_DATE, CAL_DONE_DATE,
                STATION_ID, CREATED_DATE
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [instrument_id, serial, range_val, gauge_type,
              cal_due_date, cal_done_date,
              station_id, now_ts])


def update_gauge(instrument_id, serial, range_val, gauge_type, cal_due_date, cal_done_date, active_status, station_id):
    now_ts = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE gauge_details
            SET INSTRUMENT_SER_NO=%s, `RANGE`=%s, INSTRUMENT_TYPE=%s,
                CAL_DUE_DATE=%s, CAL_DONE_DATE=%s,
                ACTIVE_STATUS=%s, STATION_ID=%s,
                UPDATED_DATE=%s
            WHERE INSTRUMENT_ID=%s
        """, [serial, range_val, gauge_type,
              cal_due_date, cal_done_date,
              active_status, station_id,
              now_ts, instrument_id])
        
        # Log the update
        cursor.execute("""
            INSERT INTO gauge_log_details (
                INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                CAL_DUE_DATE, CAL_DONE_DATE,
                STATION_ID, CREATED_DATE
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [instrument_id, serial, range_val, gauge_type,
              cal_due_date, cal_done_date,
              station_id, now_ts])


def delete_gauge_record(instrument_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM gauge_details WHERE INSTRUMENT_ID=%s", [instrument_id])


def get_gauge_by_id(instrument_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                   CAL_DUE_DATE, CAL_DONE_DATE,
                   ACTIVE_STATUS, STATION_ID
            FROM gauge_details
            WHERE INSTRUMENT_ID=%s
        """, [instrument_id])
        return cursor.fetchone()


def count_enabled_gauges_by_station(station_id, exclude_id=None):
    with connection.cursor() as cursor:
        if exclude_id:
            cursor.execute("""
                SELECT COUNT(*) FROM gauge_details 
                WHERE STATION_ID=%s AND ACTIVE_STATUS=1 AND INSTRUMENT_ID != %s
            """, [station_id, exclude_id])
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM gauge_details 
                WHERE STATION_ID=%s AND ACTIVE_STATUS=1
            """, [station_id])
        return cursor.fetchone()[0]

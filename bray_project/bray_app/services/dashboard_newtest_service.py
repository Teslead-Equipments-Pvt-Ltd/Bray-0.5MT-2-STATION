from django.db import connection

# service
def check_cyclecomplete():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, VALVE_SER_NO, SYNC_NON_SYNC_STATUS, STATION_STATUS
            FROM master_temp_data
            WHERE STATION_STATUS = %s AND CYCLE_COMPLETE = %s
        """, ['Enabled', 'No'])

        rows = cursor.fetchall()

        results = []
        for id, serial_no, sync_non_sync_status,station in rows:
            results.append({
                "id": id,
                "serial_no": serial_no,
                "mode": sync_non_sync_status,
                "station": station
            })

        return results

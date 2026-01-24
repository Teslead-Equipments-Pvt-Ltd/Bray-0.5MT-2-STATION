from django.db import connection

# def check_cyclecomplete():
#     with connection.cursor() as cursor:
#        cursor.execute("select ID, VALVE_SER_NO, STATION_STATUS,CYCLE_COMPLETE from master_temp_data where STATION_STATUS = %s and CYCLE_COMPLETE = %s",['Enabled',"No"])
#        value = cursor.fetchall()
#        print("fetched values", value)
#        if  value:
         
#          serial_no = value[0]
#          print("serail no for checkstatus", serial_no)
         
#          return value, serial_no
       

# service
def check_cyclecomplete():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, VALVE_SER_NO, STATION_STATUS
            FROM master_temp_data
            WHERE STATION_STATUS = %s AND CYCLE_COMPLETE = %s
        """, ['Enabled', 'No'])

        rows = cursor.fetchall()

        results = []
        for id, serial_no, station in rows:
            results.append({
                "id": id,
                "serial_no": serial_no,
                "station": station
            })

        return results

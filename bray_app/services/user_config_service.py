from django.db import connection

def update_hmi_disabled():
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET HMI_CONNECTION='Disabled' WHERE id=1")

def update_hmi_enabled():
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET HMI_CONNECTION='Enabled' WHERE id=1")   
        
def update_abrs_disabled():
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET ABRS_CONNECTION='Disabled' WHERE id=1")

def update_abrs_enabled():
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET ABRS_CONNECTION='Enabled' WHERE id=1")
        
def get_hmi_abrs_status(status):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET GRAPH_PDF_REPORT=%s WHERE ID=1", [status])
        
def get_pdf_status(status):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET VTR_PDF_REPORT=%s WHERE ID=1", [status])
        
def get_csv_status(status):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET VTR_CSV_REPORT=%s WHERE ID=1", [status])

def update_backup_status(status):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET AUTO_DB_BACKUP=%s WHERE ID=1", [status])
               
def get_all_toggle_value():
     with connection.cursor() as cursor:
        cursor.execute("SELECT GRAPH_PDF_REPORT,VTR_PDF_REPORT,VTR_CSV_REPORT,REPORT_PATH,AUTO_DB_BACKUP FROM configuration_table WHERE ID=1")
        return cursor.fetchone()
    
def save_report_path_db(report_path):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET REPORT_PATH=%s WHERE ID=1", [report_path])

def save_abrs_field_db(name, value):
    with connection.cursor() as cursor:

        # Get existing row
        cursor.execute("SELECT * FROM abrs_value_table WHERE ID=1")
        row = cursor.fetchone()

        # Get column names
        col_names = [desc[0] for desc in cursor.description]
        row_data = dict(zip(col_names, row))

        # First, check if the field name already exists and update it
        for i in range(1, 14):
            name_col = f"COL{i}_NAME"
            value_col = f"COL{i}_VALUE"

            if row_data.get(name_col) == name:
                # Update existing column
                cursor.execute(
                    f"""
                    UPDATE abrs_value_table
                    SET {value_col}=%s
                    WHERE ID=1
                    """,
                    [value]
                )
                return

        # If field name doesn't exist, find next empty COLx_NAME
        for i in range(1, 14):
            name_col = f"COL{i}_NAME"
            value_col = f"COL{i}_VALUE"

            if not row_data.get(name_col):
                cursor.execute(
                    f"""
                    UPDATE abrs_value_table
                    SET {name_col}=%s,
                        {value_col}=%s
                    WHERE ID=1
                    """,
                    [name, value]
                )
                break

def get_abrs_field_db():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM abrs_value_table WHERE ID=1")
        row = cursor.fetchone()

        if not row:
            return {}

        columns = [col[0] for col in cursor.description]
        row_data = dict(zip(columns, row))

        result = {}

        for i in range(1, 14):
            name = row_data.get(f"COL{i}_NAME")
            value = row_data.get(f"COL{i}_VALUE")

            if name:
                result[name] = value

        return result


# Dictionary to track logged alarms in the current session
_logged_alarms = set()
_last_alarm_id = None

def _log_alarm_if_new(cursor, alarm_id):
    global _last_alarm_id, _logged_alarms

    # If alarm changes → clear memory so next value can log again
    if alarm_id != _last_alarm_id:
        _logged_alarms.clear()

    # Save last value
    _last_alarm_id = alarm_id

    # Only log once per continuous same value
    if alarm_id not in _logged_alarms:
        cursor.execute("""
            INSERT INTO alarm_status (ALARM_CODE, ALARM_NAME)
            VALUES (%s, (SELECT ALARM_NAME FROM alarm WHERE ALARM_ID=%s))
        """, [alarm_id, alarm_id])

        _logged_alarms.add(alarm_id)   # Remember logged alarm
        return True

    return False



def get_recent_alarms(limit=4):
    """Get recent alarms from alarm_status table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ALARM_NAME, created_time 
                FROM alarm_status 
                ORDER BY created_time DESC 
                LIMIT %s
            """, [limit])
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting recent alarms: {e}")
        return []


def get_alarmname_s1(alarm_s1):
    """Get alarm name for station 1 and log it only once per occurrence"""
    try:
        with connection.cursor() as cursor:
            # Log the alarm if it's new
            _log_alarm_if_new(cursor, alarm_s1)
            
            # Get recent 4 alarms ordered by time
            cursor.execute("""
                SELECT ALARM_NAME, created_time 
                FROM alarm_status 
                ORDER BY created_time DESC 
                LIMIT 4
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error in get_alarmname_s1: {e}")
        return []




def get_alarmname_s2(alarm_s2):
    """Get alarm name for station 2 and log it only once per occurrence"""
    try:
        with connection.cursor() as cursor:
            # Log the alarm if it's new (using the same logic as station 1)
            _log_alarm_if_new(cursor, alarm_s2)
            
            # Get recent 4 alarms ordered by time
            cursor.execute("""
                SELECT ALARM_NAME, created_time 
                FROM alarm_status 
                ORDER BY created_time DESC 
                LIMIT 4
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error in get_alarmname_s2: {e}")
        return []

def insert_hmi_add(ip):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE hmi_abrs_address
            SET HMI_IP = %s
            WHERE ID = %s
            """,
            [ip,1]
        )
        return
    
def insert_abrs(abrs_host,abrs_port,abrs_db_name,abrs_username,abrs_password):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE hmi_abrs_address SET ABRS_HOST_ADDR = %s,ABRS_PORT = %s,
            ABRS_DATABASE = %s, ABRS_USERNAME = %s, ABRS_PASSWORD = %s
            WHERE ID = %s
            """,
            [abrs_host,abrs_port,abrs_db_name,abrs_username,abrs_password,1]            
        )
        return
    
def get_hmi_abrs_value():
    with connection.cursor() as cursor:
        cursor.execute("select HMI_IP,ABRS_HOST_ADDR,ABRS_PORT,ABRS_DATABASE,ABRS_USERNAME,ABRS_PASSWORD from hmi_abrs_address where ID=%s",[1])
        value = cursor.fetchone()
        return value
            
def get_hmi_address():
    with connection.cursor() as cursor:
        cursor.execute("SELECT HMI_IP FROM hmi_abrs_address WHERE ID=%s", [1])
        row = cursor.fetchone()
        if row:
            return row[0]
        return None


def get_gauge_calibration_alerts():
    """Get gauge calibration alerts for gauges due within 1-10 days"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT INSTRUMENT_SER_NO, CAL_DUE_DATE,
                   DATEDIFF(CAL_DUE_DATE, CURDATE()) as days_left
            FROM gauge_details 
            WHERE ACTIVE_STATUS = 1 
            AND CAL_DUE_DATE IS NOT NULL
            AND DATEDIFF(CAL_DUE_DATE, CURDATE()) BETWEEN 1 AND 10
            ORDER BY CAL_DUE_DATE ASC
        """)
        
        gauge_alerts = []
        rows = cursor.fetchall()
        
        for row in rows:
            instrument_ser_no = row[0]
            cal_due_date = row[1]
            days_left = row[2]
            
            if days_left == 1:
                time_text = "1 day left"
            else:
                time_text = f"{days_left} days left"
            
            gauge_alerts.append({
                'instrument_ser_no': instrument_ser_no,
                'cal_due_date': cal_due_date,
                'days_left': days_left,
                'alert_text': f"{instrument_ser_no} - Gauge calibration due - {time_text}"
            })
        
        return gauge_alerts
    
def get_abrs_address():
    with connection.cursor() as cursor:
        cursor.execute("select ABRS_HOST_ADDR,ABRS_PORT,ABRS_DATABASE,ABRS_USERNAME,ABRS_PASSWORD from SELECT * FROM bray2.hmi_abrs_address where ID-%s",[1])
        value = cursor.fetchall()
        return value
        
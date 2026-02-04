from django.db import connection
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx
from bray_app.src import HmiAddress


def get_valve_standard():
    with connection.cursor() as cursor:
        cursor.execute("SELECT STANDARD_NAME FROM standard")
        return [row[0] for row in cursor.fetchall()]
    
def get_valve_size():
    with connection.cursor() as cursor:
        cursor.execute("SELECT SIZE_NAME FROM valvesize")
        return [row[0] for row in cursor.fetchall()]

def get_valve_class():
    with connection.cursor() as cursor:
        cursor.execute("SELECT CLASS_NAME FROM valveclass")
        return [row[0] for row in cursor.fetchall()]

def get_shell_material():
    with connection.cursor() as cursor:
        cursor.execute("SELECT SHELL_MATERIAL_NAME FROM shell_material")
        return [row[0] for row in cursor.fetchall()]
    
def get_valve_type():
    with connection.cursor() as cursor:
        cursor.execute("SELECT TYPE_NAME FROM valve_type")
        return [row[0] for row in cursor.fetchall()]
    
def get_testername():
    """Get all employee names (kept for backward compatibility)"""
    with connection.cursor() as cursor:
        cursor.execute("select name from employee where superuser=%s",[0])
        return [row[0] for row in cursor.fetchall()]

def get_assemblers():
    """Get employees with type 'Approver' for Assembled By dropdown"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM employee WHERE superuser=%s AND LOWER(employee_type)=%s ORDER BY name", [0, 'approver'])
        return [row[0] for row in cursor.fetchall()]

def get_testers():
    """Get employees with type 'Tester' for Tested By dropdown"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM employee WHERE superuser=%s AND LOWER(employee_type)=%s ORDER BY name", [0, 'tester'])
        return [row[0] for row in cursor.fetchall()]


def get_testname(standard, valve_size, valve_type, shell_material, valve_class):
    with connection.cursor() as cursor:
        
        cursor.execute("SELECT STANDARD_ID FROM standard WHERE STANDARD_NAME=%s", [standard])
        standard_id = cursor.fetchone()[0]

        cursor.execute("SELECT SIZE_ID FROM valvesize WHERE SIZE_NAME=%s", [valve_size])
        size_id = cursor.fetchone()[0]

        cursor.execute("SELECT TYPE_ID FROM valve_type WHERE TYPE_NAME=%s", [valve_type])
        type_id = cursor.fetchone()[0]

        cursor.execute("SELECT TEST_ID FROM valvetype_testtype WHERE TYPE_ID=%s", [type_id])
        test_ids = cursor.fetchall()

        cursor.execute("SELECT SHELL_MATERIAL_ID FROM shell_material WHERE SHELL_MATERIAL_NAME=%s", [shell_material])
        shell_material_id = cursor.fetchone()[0]

        cursor.execute("SELECT CLASS_ID FROM valveclass WHERE CLASS_NAME=%s", [valve_class])
        class_id = cursor.fetchone()[0]

        cursor.execute("SELECT OPEN_DEGREE,CLOSE_DEGREE from master_degree_data where SIZE_ID=%s and TYPE_ID=%s",[size_id,type_id])
        degree = cursor.fetchone()
        if not degree:
            raise ValueError(f"Combination of Size '{valve_size}' and Type '{valve_type}' not found in Degree data.")
        # open_degree = degree[0]
        # close_degree = degree[1]
        # test names
        test_name = []
        for t in test_ids:
            cursor.execute("SELECT test_name FROM test_type WHERE test_id=%s", [t[0]])
            test_name.append(cursor.fetchone()[0])
        
        if not test_ids:
             raise ValueError(f"No tests found for Valve Type '{valve_type}'.")

        # pressure columns
        pressure = []
        duration = []

        for t in test_ids:
            cursor.execute("SELECT pre_col_name FROM test_type WHERE test_id=%s", [t[0]])
            pressure_rows = cursor.fetchall()

            for r in pressure_rows:
                pre_col = r[0]
                query = f"SELECT {pre_col} FROM master_pressure_data WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID=%s"
                cursor.execute(query, [shell_material_id, class_id])
                row = cursor.fetchone()
                if not row:
                     raise ValueError(f"Combination of Body Material '{shell_material}' and Class '{valve_class}' not found in Pressure data.")
                pressure.append(row[0] if row else None)

            cursor.execute("SELECT dur_col_name FROM test_type WHERE test_id=%s", [t[0]])
            duration_rows = cursor.fetchall()

            for d in duration_rows:
                dur_col = d[0]
                query = f"SELECT {dur_col} FROM master_duration_data WHERE SIZE_ID=%s AND STANDARD_ID=%s"
                cursor.execute(query, [size_id, standard_id])
                row1 = cursor.fetchone()
                if not row1:
                    raise ValueError(f"Combination of Size '{valve_size}' and Standard '{standard}' not found in Duration data.")
                duration.append(row1[0] if row1 else None)

        return test_name, pressure, duration,test_ids,degree


# ==================== STATION SERVICES ====================

def get_status():
    """Get status for both stations and sync status"""
    with connection.cursor() as cursor:
        # Fetch statuses
        cursor.execute("SELECT STATION_STATUS FROM master_temp_data WHERE id=1")
        station1_status = cursor.fetchone()[0]

        cursor.execute("SELECT STATION_STATUS FROM master_temp_data WHERE id=2")
        station2_status = cursor.fetchone()[0]
        
        # Try to read sync status from Modbus, default to 0 if it fails
        try:
            # sync_status = TestleadSmartsyncx.read_holding_registers(2018, 1).registers[0]
            sync_status=TestleadSmartsyncx.read_holding_registers(HmiAddress.SYNC_OR_NON_SYNC_MODE, 1).registers[0]
           
        except Exception as e:
            print(f"Warning: Could not read sync_status from Modbus: {e}")
            sync_status = 0  # Default to 0 (non-sync mode)
            
        print("sync_status", sync_status)
        
        return station1_status, station2_status, sync_status

def get_station_data():
    """Get data for both stations"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CLASS_NAME, SIZE_NAME, SHELL_MATERIAL_NAME, TYPE_NAME, PRESSURE_UNIT 
            FROM master_temp_data WHERE id=1
        """)
        station1_data = cursor.fetchone()

        cursor.execute("""
            SELECT CLASS_NAME, SIZE_NAME, SHELL_MATERIAL_NAME, TYPE_NAME, PRESSURE_UNIT 
            FROM master_temp_data WHERE id=2
        """)
        station2_data = cursor.fetchone()
        
        return station1_data, station2_data

def compare_station_data(station1_data, station2_data):
    """Compare data between two stations"""
    return station1_data == station2_data

def cancel_station1():
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE temp_testing_data_s1")
        # cursor.execute("TRUNCATE TABLE temp_testing_data_s2")
        cursor.execute("UPDATE master_temp_data SET STATION_STATUS=%s, CYCLE_COMPLETE=%s WHERE ID=%s", ["Disabled", "No", 1])
        # cursor.execute("UPDATE master_temp_data SET STATION_STATUS=%s, CYCLE_COMPLETE=%s WHERE ID=%s", ["Disabled", "No", 2])
        column_value = [f"COL{i}_VALUE" for i in range(1, 24)]

        set_clause = ", ".join([f"{col}=''" for col in column_value])

        cursor.execute(f"UPDATE master_temp_data SET {set_clause}")
        
def cancel_station2():
    with connection.cursor() as cursor:
        # cursor.execute("TRUNCATE TABLE temp_testing_data_s1")
        cursor.execute("TRUNCATE TABLE temp_testing_data_s2")
        # cursor.execute("UPDATE master_temp_data SET STATION_STATUS=%s, CYCLE_COMPLETE=%s WHERE ID=%s", ["Disabled", "No", 1])
        cursor.execute("UPDATE master_temp_data SET STATION_STATUS=%s, CYCLE_COMPLETE=%s WHERE ID=%s", ["Disabled", "No", 2])
        column_value = [f"COL{i}_VALUE" for i in range(1, 24)]

        set_clause = ", ".join([f"{col}=''" for col in column_value])

        cursor.execute(f"UPDATE master_temp_data SET {set_clause}")

def clear_station1():
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE temp_testing_data_s1")
        cursor.execute("UPDATE master_temp_data SET STATION_STATUS=%s, CYCLE_COMPLETE=%s WHERE ID=%s", ["Disabled", "No", 1])
        column_value = [f"COL{i}_VALUE" for i in range(1, 24)]

        set_clause = ", ".join([f"{col}=''" for col in column_value])

        cursor.execute(f"UPDATE master_temp_data SET {set_clause} WHERE ID=1")
    
def clear_station2():
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE temp_testing_data_s2")
        cursor.execute("UPDATE master_temp_data SET STATION_STATUS=%s, CYCLE_COMPLETE=%s WHERE ID=%s", ["Disabled", "No", 2])
        column_value = [f"COL{i}_VALUE" for i in range(1, 24)]

        set_clause = ", ".join([f"{col}=''" for col in column_value])

        cursor.execute(f"UPDATE master_temp_data SET {set_clause} WHERE ID=2")



    

    
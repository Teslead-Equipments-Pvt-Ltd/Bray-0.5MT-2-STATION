import json
from pymodbus.client import ModbusTcpClient
from django.db import connection, transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime
import time
from django.views.decorators.csrf import csrf_exempt
from pymodbus.client import ModbusTcpClient
import pyodbc
import threading, os
from openpyxl import Workbook
from io import BytesIO
import struct
import asyncio
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx, abrs_db
from bray_app.services.abrs_service import ABRSService
from bray_app.src import HmiAddress

from bray_app.services.syncpage_service import( 
    disable_sync_station1,
    disable_sync_station2,
    save_test_pressure_station1,
    save_test_pressure_station2,
    cycle_complete_status,
    clear_station_1,
    clear_station_2,
    clear_temp_pressure_analysis,
    clear_testing_dataS1,
    clear_testing_dataS2,
    update_tested_values_service,
    )


def getstatus(num):
    if TestleadSmartsyncx is None:
        print("[Error] HMI connection not established.")
        return None 
    try:
        return TestleadSmartsyncx.read_holding_registers(num, 1).registers[0]
    except Exception as e:
        print(f"[Error] Failed to read from register {num}: {e}")
        return None
    
    
def write_to_hmi(place, value):
    try:
        TestleadSmartsyncx.write_register(place, value)
        return True
    except Exception as e:
        print(f"[Error writing to HMI] {e}")
        isconnected = False
        return False
    

def sync_check_status(request):
    try:
        # Initialize ALL variables outside cursor block so they're accessible in response
        s1_enabled = False
        s2_enabled = False
        station1_data = None
        station2_data = None
        polling_station_id = None
        both_enabled = False
        station1_status = "Disabled"
        station2_status = "Disabled"
        is_sync_mode = False
        
        with connection.cursor() as cursor:
            # Get station statuses from database
            cursor.execute("SELECT STATION_STATUS FROM master_temp_data WHERE id=1")
            station1_status = cursor.fetchone()[0]
          
            cursor.execute("SELECT STATION_STATUS FROM master_temp_data WHERE id=2")
            station2_status = cursor.fetchone()[0]

            s1_test_mode = getstatus(HmiAddress.S1_MACHINE_MODE)

            s2_test_mode = getstatus(HmiAddress.S2_MACHINE_MODE)

        
        # Create the base response data first
        response_data = {
            "status": "success",
            "is_sync_mode": is_sync_mode,
            "station1_status": station1_status,
            "station2_status": station2_status,
            "s1_test_mode": s1_test_mode,
            "s2_test_mode": s2_test_mode,
        }
        
        print(f"Response Data: {response_data}")
        return JsonResponse(response_data)
    except Exception as e:
        print("Error in check_status:", e)
        return JsonResponse({"status": "failure", "error": str(e)})



def auto_test(request, stationNum):

    if stationNum not in [1, 2]:
        return JsonResponse({
            "status": "error",
            "message": "Invalid station number"
        }, status=400)

    # Check if both stations are in auto mode
    s1_machine_mode = getstatus(HmiAddress.S1_MACHINE_MODE)
    s2_machine_mode = getstatus(HmiAddress.S2_MACHINE_MODE)
    
    both_auto = (s1_machine_mode == 0 and s2_machine_mode == 0)
    
    if both_auto:
        # Both stations in auto mode - handle synchronization
        data = start_auto_test_both_stations(stationNum)
    elif stationNum == 1:
        data = start_auto_test_station1(stationNum)
    elif stationNum == 2:
        data = start_auto_test_station2(stationNum)
            
    return JsonResponse({
        "status": "success",
        **data
    })


def start_auto_test_both_stations(triggering_station):
    """
    Handle auto test when both stations are in auto mode.
    Synchronizes test type changes across both stations.
    """
    # Read HMI values for both stations
    s1_test_type = getstatus(HmiAddress.S1_TEST_TYPE)
    s1_hmi_test_type = getstatus(HmiAddress.S1_HIM_TEST_TYPE)
    s2_test_type = getstatus(HmiAddress.S2_TEST_TYPE)
    s2_hmi_test_type = getstatus(HmiAddress.S2_HIM_TEST_TYPE)
    test_cycle = getstatus(HmiAddress.TEST_CYCLE)

    response = {
        "station_enabled": True,
        "machine_mode": 0,  # Both in auto
        "test_id": None,
        "cycle_complete": False,
        "test_changed": False,
        "both_stations": True
    }

    # CYCLE COMPLETE - check both stations
    if test_cycle == 0:  # cycle stopped
        if s1_hmi_test_type == 0 and s2_hmi_test_type == 0:
            print("[AUTO][BOTH] Cycle stopped")
            response["cycle_complete"] = True
            # Reset test type registers for both stations
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
            return response

    # TEST CHANGE - synchronize across both stations
    if test_cycle == 1:
        # Check which station's HMI test type changed first
        s1_changed = s1_hmi_test_type != s1_test_type
        s2_changed = s2_hmi_test_type != s2_test_type
        
        if s1_changed or s2_changed:
            # Determine which test type to use (prioritize the triggering station)
            if triggering_station == 1 and s1_changed:
                new_test_type = s1_hmi_test_type
                print(f"[AUTO][BOTH] Station 1 test changed → {new_test_type}, syncing to Station 2")
            elif triggering_station == 2 and s2_changed:
                new_test_type = s2_hmi_test_type
                print(f"[AUTO][BOTH] Station 2 test changed → {new_test_type}, syncing to Station 1")
            elif s1_changed:
                # Station 1 changed (fallback)
                new_test_type = s1_hmi_test_type
                print(f"[AUTO][BOTH] Station 1 test changed → {new_test_type}, syncing to Station 2")
            else:
                # Station 2 changed (fallback)
                new_test_type = s2_hmi_test_type
                print(f"[AUTO][BOTH] Station 2 test changed → {new_test_type}, syncing to Station 1")
            
            # Write the new test type to BOTH stations simultaneously
            write_to_hmi(HmiAddress.S1_TEST_TYPE, new_test_type)
            write_to_hmi(HmiAddress.S2_TEST_TYPE, new_test_type)
            
            # Also sync the HMI test type to ensure consistency
            write_to_hmi(HmiAddress.S1_HIM_TEST_TYPE, new_test_type)
            write_to_hmi(HmiAddress.S2_HIM_TEST_TYPE, new_test_type)
            
            response["test_changed"] = True
            response["test_id"] = new_test_type
        else:
            # No change, return current test type
            response["test_id"] = s1_test_type  # Both should be the same

    return response

   

def start_auto_test_station1(stationNum):

    # --- Read HMI ---
    s1_machine_mode     = getstatus(HmiAddress.S1_MACHINE_MODE)       # 0=Auto
    s1_test_type        = getstatus(HmiAddress.S1_TEST_TYPE)
    s1_hmi_test_type    = getstatus(HmiAddress.S1_HIM_TEST_TYPE)
    test_cycle  = getstatus(HmiAddress.TEST_CYCLE)

    response = {
        "station_enabled": True,
        "machine_mode": s1_machine_mode,
        "test_id": None,
        "cycle_complete": False,
        "test_changed": False
    }

    # MANUAL MODE → do nothing
    if s1_machine_mode != 0:
        return response

    # AUTO MODE
    response["test_id"] = s1_test_type

    # CYCLE COMPLETE
    if test_cycle == 0:  # cycle stopped
        if s1_hmi_test_type == 0:
            print("[AUTO][S1] Cycle stopped")
            response["cycle_complete"] = True
            # Reset test type register
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)

    # TEST CHANGE (outside cycle complete check)
    if test_cycle == 1 and s1_hmi_test_type != s1_test_type:
        print(f"[AUTO][S1] Test changed → {s1_hmi_test_type}")
        write_to_hmi(HmiAddress.S1_TEST_TYPE, s1_hmi_test_type)
        response["test_changed"] = True
        response["test_id"] = s1_hmi_test_type

    return response



def start_auto_test_station2(stationNum):

     # --- Read HMI ---
    s2_machine_mode     = getstatus(HmiAddress.S2_MACHINE_MODE)       # 0=Auto
    s2_test_type        = getstatus(HmiAddress.S2_TEST_TYPE)
    s2_hmi_test_type    = getstatus(HmiAddress.S2_HIM_TEST_TYPE)
    test_cycle  = getstatus(HmiAddress.TEST_CYCLE)

    response = {
        "station_enabled": True,
        "machine_mode": s2_machine_mode,
        "test_id": None,
        "cycle_complete": False,
        "test_changed": False
    }

    # MANUAL MODE → do nothing
    if s2_machine_mode != 0:
        return response

    # AUTO MODE
    response["test_id"] = s2_test_type

    # CYCLE COMPLETE
    if test_cycle == 0:  # cycle stopped
        if s2_hmi_test_type == 0:
            print("[AUTO][S2] Cycle stopped")
            response["cycle_complete"] = True
            # Reset test type register
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)

    # TEST CHANGE (outside cycle complete check)
    if test_cycle == 1 and s2_hmi_test_type != s2_test_type:
        print(f"[AUTO][S2] Test changed → {s2_hmi_test_type}")
        write_to_hmi(HmiAddress.S2_TEST_TYPE, s2_hmi_test_type)
        response["test_changed"] = True
        response["test_id"] = s2_hmi_test_type

    return response


def get_station_values(request, stationId):
    """
    Get station values including valve info, size, class, material, etc.
    """
    try:
        with connection.cursor() as cursor:
            # Handle 'both' case - fetch from both stations
            if stationId == 'both':
                # Fetch station 1 data
                cursor.execute("""
                    SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME, PRESSURE_UNIT, 
                           SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS
                    FROM master_temp_data
                    WHERE id = 1
                """)
                s1_row = cursor.fetchone()
                
                # Fetch station 2 data
                cursor.execute("""
                    SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME, PRESSURE_UNIT, 
                           SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS
                    FROM master_temp_data
                    WHERE id = 2
                """)
                s2_row = cursor.fetchone()
                
                if s1_row and s2_row:
                    # Get torque values from HMI for both stations
                    s1_open_torque = getstatus(HmiAddress.S1_SET_OPEN_TORQUE)
                    s1_close_torque = getstatus(HmiAddress.S1_SET_CLOSE_TORQUE)
                    s2_open_torque = getstatus(HmiAddress.S2_SET_OPEN_TORQUE)
                    s2_close_torque = getstatus(HmiAddress.S2_SET_CLOSE_TORQUE)
                    
                    # Use station 1 values for common fields (size, class, material, etc.)
                    # Include both valve serial numbers and both torques
                    both_data = {
                        "status": "success",
                        "station_id": "both",
                        "s1_valve_serial_no": s1_row[0],
                        "s2_valve_serial_no": s2_row[0],
                        "size": s1_row[1],
                        "class": s1_row[2],
                        "pressure_unit": s1_row[3],
                        "body_material": s1_row[4],
                        "assembled_by": s1_row[5],
                        "tested_by": s1_row[6],
                        "s1_open_torque": s1_open_torque,
                        "s1_close_torque": s1_close_torque,
                        "s2_open_torque": s2_open_torque,
                        "s2_close_torque": s2_close_torque
                    }

                    both_size = s1_row[1]
                    both_class_name = s1_row[2]
                    both_pressure_unit = s1_row[3] 
                    both_station_status = s1_row[7]

                    cursor.execute("""
                        SELECT SIZE_ID, SIZE_NAME  
                        FROM valvesize
                        WHERE SIZE_NAME = %s
                        """, [both_size])
                    both_v_size = cursor.fetchone()  

                    if both_v_size:
                        b_size_id = both_v_size[0]     
                        write_to_hmi(HmiAddress.S1_VALVE_SIZE, b_size_id)
                        write_to_hmi(HmiAddress.S2_VALVE_SIZE, b_size_id)

                    #station 1 write
                    write_to_hmi(HmiAddress.S1_VALVE_CALSS, both_class_name)
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, both_pressure_unit)
                    write_to_hmi(HmiAddress.S1_E_D_STATUS, 1 if both_station_status == "Enabled" else 0)
                    #station 2 write
                    write_to_hmi(HmiAddress.S2_VALVE_CALSS, both_class_name)
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, both_pressure_unit)
                    write_to_hmi(HmiAddress.S2_E_D_STATUS, 1 if both_station_status == "Enabled" else 0)

                    return JsonResponse(both_data)
                else:
                    return JsonResponse({"status": "error", "message": "Data not found for one or both stations"})
            
            # Handle station 1
            elif stationId == '1':
                cursor.execute("""
                    SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME, PRESSURE_UNIT, 
                           SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS
                    FROM master_temp_data
                    WHERE id = 1
                """)
                s1_row = cursor.fetchone()
                
                if s1_row:
                    # Get torque values from HMI
                    s1_open_torque = getstatus(HmiAddress.S1_SET_OPEN_TORQUE)
                    s1_close_torque = getstatus(HmiAddress.S1_SET_CLOSE_TORQUE)
                    
                    station1_data = {
                        "status": "success",
                        "station_id": 1,
                        "valve_serial_no": s1_row[0],
                        "size": s1_row[1],
                        "class": s1_row[2],
                        "pressure_unit": s1_row[3],
                        "body_material": s1_row[4],
                        "assembled_by": s1_row[5],
                        "tested_by": s1_row[6],
                        "open_torque": s1_open_torque,
                        "close_torque": s1_close_torque
                    }

                    size = s1_row[1]
                    class_name = s1_row[2]
                    pressure_unit = s1_row[3]
                    station_status = s1_row[7]

                    cursor.execute("""
                        SELECT SIZE_ID, SIZE_NAME  
                        FROM valvesize
                        WHERE SIZE_NAME = %s
                        """, [size])
                    s1_v_size = cursor.fetchone()   
            
                    #hmi write
                    if s1_v_size:
                        s1_size_id = s1_v_size[0]     
                        write_to_hmi(HmiAddress.S1_VALVE_SIZE, s1_size_id)

                    write_to_hmi(HmiAddress.S1_VALVE_CALSS, class_name)
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, pressure_unit)
                    write_to_hmi(HmiAddress.S1_E_D_STATUS, 1 if station_status == "Enabled" else 0)

                    return JsonResponse(station1_data)
                else:
                    return JsonResponse({"status": "error", "message": "No data found for station 1"})
            
            # Handle station 2
            elif stationId == '2':
                cursor.execute("""
                    SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME, PRESSURE_UNIT, 
                           SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS
                    FROM master_temp_data
                    WHERE id = 2
                """)
                s2_row = cursor.fetchone()
                
                if s2_row:
                    # Get torque values from HMI
                    s2_open_torque = getstatus(HmiAddress.S2_SET_OPEN_TORQUE)
                    s2_close_torque = getstatus(HmiAddress.S2_SET_CLOSE_TORQUE)
                    
                    station2_data = {
                        "status": "success",
                        "station_id": 2,
                        "valve_serial_no": s2_row[0],
                        "size": s2_row[1],
                        "class": s2_row[2],
                        "pressure_unit": s2_row[3],
                        "body_material": s2_row[4],
                        "assembled_by": s2_row[5],
                        "tested_by": s2_row[6],
                        "open_torque": s2_open_torque,
                        "close_torque": s2_close_torque
                    }
                    
                    size2 = s2_row[1]
                    class_name2 = s2_row[2]
                    pressure_unit2 = s2_row[3]
                    station_status2 = s2_row[7]

                    cursor.execute("""
                        SELECT SIZE_ID, SIZE_NAME  
                        FROM valvesize
                        WHERE SIZE_NAME = %s
                        """, [size2])
                    s2_v_size = cursor.fetchone()   
            
                    #hmi write
                    if s2_v_size:
                        s2_size_id = s2_v_size[0]     
                        write_to_hmi(HmiAddress.S2_VALVE_SIZE, s2_size_id)

                    write_to_hmi(HmiAddress.S2_VALVE_CALSS, class_name2)
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, pressure_unit2)
                    write_to_hmi(HmiAddress.S2_E_D_STATUS, 1 if station_status2 == "Enabled" else 0)
                    
                    return JsonResponse(station2_data)
                else:
                    return JsonResponse({"status": "error", "message": "No data found for station 2"})
            
            else:
                return JsonResponse({"status": "error", "message": "Invalid station ID"})
                
    except Exception as e:
        print("Error in get_station_values:", e)
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)})


def sync_enabled_test_buttons(request, stationId):
    """
    Fetch enabled test buttons based on station_id
    station_id can be: 1, 2, or 'both'
    """
    try:
        with connection.cursor() as cursor:
            # Determine which table to query based on station_id
            if stationId == 'both' or stationId == '1':
                # For both stations or station 1, get station 1 buttons
                cursor.execute("""
                    SELECT TEST_ID, VALVE_SERIAL_NO, TEST_NAME, TESTING_PR_UNIT, TESTING_DUR_UNIT 
                    FROM temp_testing_data_s1
                """)
                test_buttons = cursor.fetchall()
                
            elif stationId == '2':
                # For station 2, get station 2 buttons
                cursor.execute("""
                    SELECT TEST_ID, VALVE_SERIAL_NO, TEST_NAME, TESTING_PR_UNIT, TESTING_DUR_UNIT 
                    FROM temp_testing_data_s2
                """)
                test_buttons = cursor.fetchall()
            else:
                # Invalid station_id
                return JsonResponse({
                    "status": "error",
                    "message": f"Invalid station_id: {stationId}"
                })
            
            # Format the button data
            enabled_test_buttons = []
            for btn in test_buttons:
                enabled_test_buttons.append({
                    "id": btn[0],
                    "valve_serial_no": btn[1],
                    "name": btn[2],
                    "psr_unit": btn[3],
                    "dur_unit": btn[4]
                })

            print(f"Fetched {len(enabled_test_buttons)} test buttons for station {stationId}")

        return JsonResponse({
            "status": "success",
            "station_id": stationId,
            "enabled_test_buttons": enabled_test_buttons
        })
        
    except Exception as e:
        print(f"Error in sync_enabled_test_buttons: {e}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })



#=================================Get SET values, START thread and store SET values in respective table functions ===============================================#

def get_set_pressure(request, stationId, id, name, valve_serial_no, psr_unit):
    """
    Main function to get and set pressure based on station ID
    station_id can be: 'both', '1', or '2'
    If station_id is 'both', fetches and writes to both stations
    """
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        print(f"get_set_pressure called with: station_id={stationId}, id={id}, name={name}, valve_serial_no={valve_serial_no}, psr_unit={psr_unit}")
        
        # Handle 'both' case - fetch from both stations
        if stationId == "both":
            print("Station ID is 'both', fetching data from both stations")
            
            # Get station data from check_status to determine valve serial numbers
            with connection.cursor() as cursor:
                cursor.execute("SELECT VALVE_SER_NO FROM master_temp_data WHERE id=1")
                s1_valve_row = cursor.fetchone()
                s1_valve_serial = s1_valve_row[0] if s1_valve_row else valve_serial_no
                
                cursor.execute("SELECT VALVE_SER_NO FROM master_temp_data WHERE id=2")
                s2_valve_row = cursor.fetchone()
                s2_valve_serial = s2_valve_row[0] if s2_valve_row else valve_serial_no
            
            # Fetch station 1 data
            station1_response = set_pressure_station1(id, name, s1_valve_serial, psr_unit)
            station1_data = station1_response.content.decode('utf-8')
            station1_json = json.loads(station1_data)
            
            # Fetch station 2 data
            station2_response = set_pressure_station2(id, name, s2_valve_serial, psr_unit)
            station2_data = station2_response.content.decode('utf-8')
            station2_json = json.loads(station2_data)
            
            # Start threads for both stations after setting pressure
            start_station_threads(station1_enabled=True, station2_enabled=True)
            
            # Return combined response
            return JsonResponse({
                "status": "success",
                "station_id": "both",
                "station1_value": station1_json.get("station1_value"),
                "station2_value": station2_json.get("station2_value")
            })
        
        # Handle station 1
        elif stationId == "1" or stationId == 1:
            print("Station ID is 1")
            response = set_pressure_station1(id, name, valve_serial_no, psr_unit)
            # Start thread for station 1 after setting pressure
            start_station_threads(station1_enabled=True, station2_enabled=False)
            return response
        
        # Handle station 2
        elif stationId == "2" or stationId == 2:
            print("Station ID is 2")
            response = set_pressure_station2(id, name, valve_serial_no, psr_unit)
            # Start thread for station 2 after setting pressure
            start_station_threads(station1_enabled=False, station2_enabled=True)
            return response
        
        else:
            return JsonResponse({
                "status": "error",
                "message": f"Invalid station_id: {stationId}"
            }, status=400)
            
    except Exception as e:
        print(f"ERROR in get_set_pressure: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)




def set_pressure_station1(id, name, valve_serial_no, psr_unit):
    """
    Set pressure values for station 1 and return test data
    """
    try:
        print(f"set_pressure_station1: id={id}, name={name}, valve_serial_no={valve_serial_no}, psr_unit={psr_unit}")
         
        allowed_units = ["BAR", "PSI", "KG"]

        if psr_unit not in allowed_units:
            raise ValueError("Invalid unit type")
        
        column_name = f"TESTING_PR_{psr_unit}" 

        set_bubble_count = getstatus(HmiAddress.S1_SET_BUBBLE_COUNT)
        set_clampping_psr = getstatus(HmiAddress.S1_SET_CLAMPING_PRESSURE)
                
        with connection.cursor() as cursor:
            query = f"""
                    SELECT VALVE_SERIAL_NO, TEST_ID, TEST_NAME, TEST_MEDIUM,
                    TEST_CATEGORY, TESTING_PR_UNIT, {column_name}, TESTING_DUR_UNIT, TESTING_DUR_SEC
                    FROM temp_testing_data_s1
                    WHERE TEST_ID = %s AND TEST_NAME = %s
                """
            cursor.execute(query, [id, name])
            station_1 = cursor.fetchall()

            station_data1 = {}

            for row in station_1:
                s1_valve_serial_no = row[0]
                test_id = row[1]
                test_name = row[2]
                pressure_unit = row[5]
                set_pressure = row[6]
                dur_unit = row[7]
                set_duration = row[8]

                station_data1 = {
                    "VALVE_SERIAL_NO": s1_valve_serial_no,
                    "TEST_ID": test_id,
                    "TEST_NAME": test_name,
                    "TESTING_PSR_UNIT": pressure_unit,
                    "TESTING_PRESSURE": set_pressure,
                    "TESTING_DUR_UNIT": dur_unit,
                    "TESTING_DUR": set_duration,
                    "set_clampping_psr": set_clampping_psr,
                    "set_bubble_count": set_bubble_count
                }

            query3 = f"""
                SELECT CLASS_NAME
                FROM master_temp_data
                WHERE VALVE_SER_NO = %s
            """
            cursor.execute(query3, [valve_serial_no])
            station1_cls = cursor.fetchone()
            print("station1_cls:", station1_cls)

            
            
            cursor.execute("""
            SELECT CLASS_ID, CLASS_NAME  
            FROM valveclass
            WHERE CLASS_NAME = %s
            """, [station1_cls])
            s1_v_class = cursor.fetchone()   
            print("class id", s1_v_class)
        
            #hmi write
            if s1_v_class:
                s1_class = s1_v_class[0]     
                

                write_to_hmi(HmiAddress.S1_SET_PRESSURE, int(set_pressure))

                write_to_hmi(HmiAddress.S1_SET_TEST_TIME, int(set_duration))
                write_to_hmi(HmiAddress.S1_VALVE_CALSS, int(s1_class))
                
                if pressure_unit.lower() == 'psi':
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, 1)

                elif pressure_unit.lower() == 'bar':
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, 2)

                else:
                    pressure_unit.lower() == 'kg/cm2g'
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, 3)

                
                write_to_hmi(HmiAddress.S1_TEST_TYPE, int(test_id))

                master_query = f"""
                        SELECT STANDARD_NAME, SIZE_NAME, TYPE_NAME, CLASS_NAME, SHELL_MATERIAL_NAME, 
                        COL1_NAME, COL1_VALUE, 
                        COL2_NAME, COL2_VALUE,
                        COL3_NAME, COL3_VALUE,
                        COL4_NAME, COL4_VALUE,
                        COL5_NAME, COL5_VALUE,
                        COL6_NAME, COL6_VALUE,
                        COL7_NAME, COL7_VALUE,
                        COL8_NAME, COL8_VALUE,
                        COL9_NAME, COL9_VALUE,
                        COL10_NAME, COL10_VALUE,
                        COL11_NAME, COL11_VALUE,
                        COL12_NAME, COL12_VALUE,
                        COL13_NAME, COL13_VALUE,
                        COL14_NAME, COL14_VALUE,
                        COL15_NAME, COL15_VALUE,
                        COL16_NAME, COL16_VALUE,
                        COL17_NAME, COL17_VALUE,
                        COL18_NAME, COL18_VALUE,
                        COL19_NAME, COL19_VALUE,
                        COL20_NAME, COL20_VALUE,
                        COL21_NAME, COL21_VALUE,
                        COL22_NAME, COL22_VALUE,
                        COL23_NAME, COL23_VALUE,
                        COL24_NAME, COL24_VALUE

                        FROM master_temp_data
                        WHERE VALVE_SER_NO = %s
                """
            cursor.execute(master_query, [valve_serial_no])
            master_data = cursor.fetchone()
            

            if not master_data:
                raise ValueError("No master data found for given VALVE_SER_NO")
            
            columns = [col[0] for col in cursor.description]
            data = dict(zip(columns, master_data))
            
            parameters = {}

            for i in range(1, 25):
                col_name = data.get(f"COL{i}_NAME")
                value = data.get(f"COL{i}_VALUE")

                if col_name:  # ignore empty/null columns
                    parameters[col_name] = value
                    

            final_data_1 = {
                "STANDARD_NAME": data["STANDARD_NAME"],
                "SIZE_NAME": data["SIZE_NAME"],
                "TYPE_NAME": data["TYPE_NAME"],
                "CLASS_NAME": data["CLASS_NAME"],
                "SHELL_MATERIAL_NAME": data["SHELL_MATERIAL_NAME"],
                "PARAMETERS": parameters,
            }

            save_test_pressure_station1(id, name, valve_serial_no, station_data1, final_data_1, cursor)
            

        return JsonResponse({
            "status": "success",
            "station": 1,
            "station1_value": station_data1
        }, safe=False)
    
    except Exception as e:
        print(f"ERROR in set_pressure_station1: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

        



def set_pressure_station2(id, name, valve_serial_no, psr_unit):
    """
    Set pressure values for station 2 and return test data
    """
    try:
        print(f"set_pressure_station2: id={id}, name={name}, valve_serial_no={valve_serial_no}, psr_unit={psr_unit}")
        
        allowed_units = ["BAR", "PSI", "KG"]

        if psr_unit not in allowed_units:
            raise ValueError("Invalid unit type")
        
        column_name = f"TESTING_PR_{psr_unit}" 

        s2_set_bubble_count = getstatus(HmiAddress.S2_SET_BUBBLE_COUNT)
        s2_set_clampping_psr = getstatus(HmiAddress.S2_SET_CLAMPING_PRESSURE)

        with connection.cursor() as cursor:
            query2 = f"""
                    SELECT VALVE_SERIAL_NO, TEST_ID, TEST_NAME, TEST_MEDIUM,
                    TEST_CATEGORY, TESTING_PR_UNIT, {column_name}, TESTING_DUR_UNIT, TESTING_DUR_SEC
                    FROM temp_testing_data_s2
                    WHERE TEST_ID = %s AND TEST_NAME = %s
                """
            cursor.execute(query2, [id, name])
            station_2 = cursor.fetchall()
            print("station 2 values in temp_testing_data", station_2)

            station2_data = {}

            for row in station_2:
                s2_valve_serial_no = row[0]
                s2_test_id = row[1]
                s2_test_name = row[2]
                s2_pressure_unit = row[5]
                s2_set_pressure = row[6]
                s2_dur_unit = row[7]
                s2_set_duration = row[8]
                
                station2_data = {
                    "VALVE_SERIAL_NO": s2_valve_serial_no,
                    "TEST_ID": s2_test_id,
                    "TEST_NAME": s2_test_name,
                    "TESTING_PSR_UNIT": s2_pressure_unit,
                    "TESTING_PRESSURE": s2_set_pressure,
                    "TESTING_DUR_UNIT": s2_dur_unit,
                    "TESTING_DUR": s2_set_duration,
                    "set_clampping_psr": s2_set_clampping_psr,
                    "set_bubble_count": s2_set_bubble_count
                }
                
            vc_query = f"""
                SELECT CLASS_NAME
                FROM master_temp_data
                WHERE VALVE_SER_NO = %s
            """
            cursor.execute(vc_query, [valve_serial_no])
            station2_cls = cursor.fetchone()

            cursor.execute("""
            SELECT CLASS_ID, CLASS_NAME  
            FROM valveclass
            WHERE CLASS_NAME = %s
            """, [station2_cls])
            s2_v_class = cursor.fetchone()   
            print("class id", s2_v_class)
        
            #hmi write
            if s2_v_class:
                s2_class = s2_v_class[0]     
                
                write_to_hmi(HmiAddress.S2_SET_PRESSURE, int(s2_set_pressure))
                write_to_hmi(HmiAddress.S2_SET_TEST_TIME, int(s2_set_duration))
                write_to_hmi(HmiAddress.S2_VALVE_CALSS, int(s2_class))
                
                if s2_pressure_unit.lower() == 'psi':
                    write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, 1)

                elif s2_pressure_unit.lower() == 'bar':
                    write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, 2)

                else:
                    s2_pressure_unit.lower() == 'kg/cm2g'
                    write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, 3)

                write_to_hmi(HmiAddress.S2_TEST_TYPE, int(s2_test_id))
        
                master_query2 = f"""
                        SELECT STANDARD_NAME, SIZE_NAME, TYPE_NAME, CLASS_NAME, SHELL_MATERIAL_NAME, 
                        COL1_NAME, COL1_VALUE, 
                        COL2_NAME, COL2_VALUE,
                        COL3_NAME, COL3_VALUE,
                        COL4_NAME, COL4_VALUE,
                        COL5_NAME, COL5_VALUE,
                        COL6_NAME, COL6_VALUE,
                        COL7_NAME, COL7_VALUE,
                        COL8_NAME, COL8_VALUE,
                        COL9_NAME, COL9_VALUE,
                        COL10_NAME, COL10_VALUE,
                        COL11_NAME, COL11_VALUE,
                        COL12_NAME, COL12_VALUE,
                        COL13_NAME, COL13_VALUE,
                        COL14_NAME, COL14_VALUE,
                        COL15_NAME, COL15_VALUE,
                        COL16_NAME, COL16_VALUE,
                        COL17_NAME, COL17_VALUE,
                        COL18_NAME, COL18_VALUE,
                        COL19_NAME, COL19_VALUE,
                        COL20_NAME, COL20_VALUE,
                        COL21_NAME, COL21_VALUE,
                        COL22_NAME, COL22_VALUE,
                        COL23_NAME, COL23_VALUE,
                        COL24_NAME, COL24_VALUE

                        FROM master_temp_data
                        WHERE VALVE_SER_NO = %s
                    """
            cursor.execute(master_query2, [valve_serial_no])
            master_data_2 = cursor.fetchone()
            

            if not master_data_2:
                raise ValueError("No master data found for given VALVE_SER_NO")
            
            columns_2 = [col[0] for col in cursor.description]
            data_2 = dict(zip(columns_2, master_data_2))
            
            parameters_2 = {}

            for i in range(1, 25):
                col_name = data_2.get(f"COL{i}_NAME")
                value = data_2.get(f"COL{i}_VALUE")

                if col_name:  # ignore empty/null columns
                    parameters_2[col_name] = value
                    

            final_data_2 = {
                "STANDARD_NAME": data_2["STANDARD_NAME"],
                "SIZE_NAME": data_2["SIZE_NAME"],
                "TYPE_NAME": data_2["TYPE_NAME"],
                "CLASS_NAME": data_2["CLASS_NAME"],
                "SHELL_MATERIAL_NAME": data_2["SHELL_MATERIAL_NAME"],
                "PARAMETERS": parameters_2
            }

            save_test_pressure_station2(id, name, valve_serial_no, station2_data, final_data_2, cursor)
            

        return JsonResponse({
            "status": "success",
            "station": 2,
            "station2_value": station2_data
        }, safe=False)
    
    except Exception as e:
        print(f"ERROR in set_pressure_station2: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

#===============================================================================================================#


#================================Thread functions to start and stop threads  ===================================#

station1_thread = None
station2_thread = None

station1_enabled = getstatus(HmiAddress.S1_E_D_STATUS) == 1
station2_enabled = getstatus(HmiAddress.S2_E_D_STATUS) == 1

station1_stop = threading.Event()
station2_stop = threading.Event()

def start_station_threads(station1_enabled = False, station2_enabled = False):
    global station1_thread, station2_thread

    # Station 1
    if station1_enabled:
        if not station1_thread or not station1_thread.is_alive():
            station1_stop.clear()
            station1_thread = threading.Thread(
                target=store_pressure_station1,
                daemon=True
            )
            station1_thread.start()
            print("Started Station-1 thread")
    

    # Station 2
    if station2_enabled:
        if not station2_thread or not station2_thread.is_alive():
            station2_stop.clear()
            station2_thread = threading.Thread(
                target=store_pressure_station2,
                daemon=True
            )
            station2_thread.start()
            print("Started Station-2 thread")


# Global variables to track timer synchronization across both stations
controlling_timer_station = None  # Which station's timer is controlling (1 or 2)
s1_previous_timer_status = None
s2_previous_timer_status = None
sync_timer_lock = threading.Lock()  # Thread lock for safe access


def store_pressure_station1():
    global controlling_timer_station, s1_previous_timer_status, s2_previous_timer_status
    print("Station-1 pressure thread started")

    while not station1_stop.is_set():
        try:
            # Read both HMI timer statuses to determine which one is controlling
            s1_timer_status = getstatus(HmiAddress.S1_TIMER_STATUS)
            s2_timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)
            
            with connection.cursor() as cursor:
                # Check if both stations are enabled
                cursor.execute("SELECT COUNT(*) FROM master_temp_data WHERE STATION_STATUS='Enabled'")
                enabled_count = cursor.fetchone()[0]
                both_stations_enabled = enabled_count == 2
                
                # Determine which timer status to use
                with sync_timer_lock:
                    if both_stations_enabled:
                        # Determine controlling station based on which timer changed first
                        if controlling_timer_station is None:
                            # No controlling station yet - check which one starts first
                            if s1_timer_status == 1 and s1_previous_timer_status != 1:
                                controlling_timer_station = 1
                                print("✓ Station 1 timer started first - S1 is now controlling")
                            elif s2_timer_status == 1 and s2_previous_timer_status != 1:
                                controlling_timer_station = 2
                                print("✓ Station 2 timer started first - S2 is now controlling")
                        
                        # Check if controlling station timer stopped (reset control)
                        if controlling_timer_station == 1 and s1_timer_status == 0 and s1_previous_timer_status == 1:
                            print("✓ Station 1 timer stopped - resetting control")
                            controlling_timer_station = None
                        elif controlling_timer_station == 2 and s2_timer_status == 0 and s2_previous_timer_status == 1:
                            print("✓ Station 2 timer stopped - resetting control")
                            controlling_timer_station = None
                        
                        # Use controlling station's timer status, or S1 if no controller
                        if controlling_timer_station == 2:
                            active_timer_status = s2_timer_status
                            print(f"Using S2 timer status: {active_timer_status}")
                        else:
                            active_timer_status = s1_timer_status
                            print(f"Using S1 timer status: {active_timer_status}")
                        
                        # Update previous statuses
                        s1_previous_timer_status = s1_timer_status
                        s2_previous_timer_status = s2_timer_status
                    else:
                        # Only station 1 enabled - use its own timer
                        active_timer_status = s1_timer_status
                
                # Get Station 1 data
                query = """
                    SELECT VALVE_SER_NO, PRESSURE_UNIT
                    FROM master_temp_data
                    WHERE STATION_STATUS = "Enabled" and ID = 1
                """
                cursor.execute(query)
                pressure_valveserial = cursor.fetchall()

                for row in pressure_valveserial:
                    serial_no = row[0]
                    pressure_unit = row[1].lower()
                    
                    # Read pressure based on unit
                    if pressure_unit == 'psi':
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                    elif pressure_unit == 'bar':
                        pressure_bar = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                        pressure = pressure_bar / 10
                    elif pressure_unit == 'kg/cm2g':
                        pressure_kg = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                        pressure = pressure_kg / 10
                    else:
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                
                    # Read other HMI values
                    result = getstatus(HmiAddress.S1_TEST_RESULT)
                    s1_test_id = getstatus(HmiAddress.S1_TEST_TYPE)

                    query = """
                        SELECT TEST_NAME
                        FROM temp_testing_data_s1
                        WHERE TEST_ID = %s
                    """
                    cursor.execute(query, [s1_test_id])
                    s1_row = cursor.fetchone()
                    s1_test_name = s1_row[0] if s1_row else None

            # Insert data for Station 1 with the active timer status
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO current_status_station1
                    (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [serial_no, s1_test_id, s1_test_name, pressure, active_timer_status, result])
                
                # If both stations enabled, also insert for Station 2 with same timer status
                if both_stations_enabled:
                    cursor.execute("""
                        SELECT VALVE_SER_NO, PRESSURE_UNIT
                        FROM master_temp_data
                        WHERE STATION_STATUS = "Enabled" and ID = 2
                    """)
                    s2_row = cursor.fetchone()
                    
                    if s2_row:
                        s2_serial_no = s2_row[0]
                        s2_test_id = getstatus(HmiAddress.S2_TEST_TYPE)
                        
                        # Get test name for station 2
                        cursor.execute("""
                            SELECT TEST_NAME
                            FROM temp_testing_data_s2
                            WHERE TEST_ID = %s
                        """, [s2_test_id])
                        s2_test_row = cursor.fetchone()
                        s2_test_name = s2_test_row[0] if s2_test_row else None
                        
                        # Get current pressure for station 2
                        s2_pressure_unit = s2_row[1].lower()
                        if s2_pressure_unit == 'psi':
                            s2_pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        elif s2_pressure_unit == 'bar':
                            s2_pressure_bar = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                            s2_pressure = s2_pressure_bar / 10
                        elif s2_pressure_unit == 'kg/cm2g':
                            s2_pressure_kg = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                            s2_pressure = s2_pressure_kg / 10
                        else:
                            s2_pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        
                        s2_result = getstatus(HmiAddress.S2_TEST_RESULT)
                        
                        # Insert for station 2 with SAME timer status
                        cursor.execute("""
                            INSERT INTO current_status_station2
                            (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, [s2_serial_no, s2_test_id, s2_test_name, s2_pressure, active_timer_status, s2_result])
                        
                        print(f"✓ S1 Thread: Synced timer_status={active_timer_status} to both stations")

            print(f"S1 Thread: Serial={serial_no}, Pressure={pressure}, Test_ID={s1_test_id}, Timer={active_timer_status}")

        except Exception as e:
            print("S1 error:", e)
            import traceback
            traceback.print_exc()

        time.sleep(1)


def store_pressure_station2():
    global controlling_timer_station, s1_previous_timer_status, s2_previous_timer_status
    print("Station-2 pressure thread started")

    while not station2_stop.is_set():
        try:
            with connection.cursor() as cursor:
                # Check if both stations are enabled
                cursor.execute("SELECT COUNT(*) FROM master_temp_data WHERE STATION_STATUS='Enabled'")
                enabled_count = cursor.fetchone()[0]
                both_stations_enabled = enabled_count == 2
                
                # If both stations enabled, S1 thread handles everything - skip this iteration
                if both_stations_enabled:
                    print("S2 Thread: Both stations enabled - S1 thread handling synchronization")
                    time.sleep(1)
                    continue
                
                # Only Station 2 is enabled - handle it independently
                query = """
                    SELECT VALVE_SER_NO, PRESSURE_UNIT
                    FROM master_temp_data
                    WHERE STATION_STATUS = "Enabled" and ID = 2
                """
                cursor.execute(query)
                pressure_valveserial = cursor.fetchall()

                for row in pressure_valveserial:
                    serial_no = row[0]
                    pressure_unit = row[1].lower()
                    
                    # Read pressure based on unit
                    if pressure_unit == 'psi':
                        pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                    elif pressure_unit == 'bar':
                        pressure_bar = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        pressure = pressure_bar / 10
                    elif pressure_unit == 'kg/cm2g':
                        pressure_kg = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        pressure = pressure_kg / 10
                    else:
                        pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                
                    # Read other HMI values
                    result = getstatus(HmiAddress.S2_TEST_RESULT)
                    timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)
                    s2_test_id = getstatus(HmiAddress.S2_TEST_TYPE)

                    query = """
                        SELECT TEST_NAME
                        FROM temp_testing_data_s2
                        WHERE TEST_ID = %s
                    """
                    cursor.execute(query, [s2_test_id])
                    s2_row = cursor.fetchone()
                    s2_test_name = s2_row[0] if s2_row else None

            # Insert data for Station 2 only (single station mode)
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO current_status_station2
                    (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [serial_no, s2_test_id, s2_test_name, pressure, timer_status, result])

            print(f"S2 Thread (Solo): Serial={serial_no}, Pressure={pressure}, Test_ID={s2_test_id}, Timer={timer_status}")

        except Exception as e:
            print("S2 error:", e)
            import traceback
            traceback.print_exc()

        time.sleep(1)




def stop_station1():
    global station1_thread
    if station1_thread and station1_thread.is_alive():
        station1_stop.set()
        print("Stopping Station-1 thread...")
        station1_thread.join(timeout=5.0)  # Wait up to 5 seconds for thread to finish
        if station1_thread.is_alive():
            print("[WARNING] Station-1 thread did not stop within timeout")
        else:
            print("Station-1 thread stopped successfully")
            station1_thread = None

def stop_station2():
    global station2_thread
    if station2_thread and station2_thread.is_alive():
        station2_stop.set()
        print("Stopping Station-2 thread...")
        station2_thread.join(timeout=5.0)  # Wait up to 5 seconds for thread to finish
        if station2_thread.is_alive():
            print("[WARNING] Station-2 thread did not stop within timeout")
        else:
            print("Station-2 thread stopped successfully")
            station2_thread = None


#=================================================================================================================#


def sync_live_values(request, stationId, id, valve_serial_no):
    # Convert stationId to appropriate type for comparison
    # It can be passed as string or int from URL
    try:
        station_id_int = int(stationId)
        stationId = station_id_int
    except (ValueError, TypeError):
        # stationId might be "both" or invalid
        pass
    
    if stationId not in [1, 2, "both"]:
        return JsonResponse({"error": "Invalid station"}, status=400)

    data = None
    
    if stationId == 1:
        data = get_sync_live_pressure_data1(request, id, valve_serial_no, stationId)

    elif stationId == 2:
        data = get_sync_live_pressure_data2(request, id, valve_serial_no, stationId)

    elif stationId == "both":
        # This case should not normally be called since frontend polls each station separately
        # But we handle it just in case
        data = get_sync_live_pressure_data1(request, id, valve_serial_no, 1)

    if data is None:
        return JsonResponse({
            "status": "error",
            "message": "No data available"
        }, status=500)

    return JsonResponse({
        "status": "success",
        "station": stationId,
        "data": data
    })




def get_sync_live_pressure_data1(request, id, valve_serial_no, stationId):

    actual_pre = None
    actual_timer_status = None
    actual_time = None
    result = None

    with connection.cursor() as cursor:

        # CASE 1: Initial live pressure (NO test yet)
        if int(id) == 0:
            cursor.execute("""
                SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
                FROM current_status_station1
                WHERE VALVE_SERIAL_NO = %s
                ORDER BY id DESC
                LIMIT 10
            """, [valve_serial_no])

        # # CASE 2: Test running (test-specific pressure)
        else:
            cursor.execute("""
                SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
                FROM current_status_station1
                WHERE TEST_ID = %s AND VALVE_SERIAL_NO = %s
                ORDER BY id DESC
                LIMIT 1
            """, [id, valve_serial_no])

        value1 = cursor.fetchone()
       
        actual_duration = getstatus(HmiAddress. S1_ACTUAL_TEST_TIME)
        actual_open_torque = getstatus(HmiAddress.S1_ACTUAL_OPEN_TORQUE)
        actual_close_torque =getstatus(HmiAddress.S1_ACTUAL_CLOSE_TORQUE )
        result_value1 = getstatus(HmiAddress.S1_TEST_RESULT)
        actual_bubble = getstatus(HmiAddress.S1_ACTUAL_BUBBLE_COUNT)
        actual_clamping_psr=getstatus(HmiAddress.S1_ACTUAL_CALMPING_PRESSURE)
        # leak_pressure = getstatus(HmiAddress.)

        if value1:
            actual_pre = value1[0]
            actual_timer_status = value1[1]
            actual_time = value1[2]
            result = value1[3]

    return {
        "connected": True,
        "current_pressure": float(actual_pre) if actual_pre is not None else 0.0,
        "timestamp": str(actual_time) if actual_time else "",
        "timerStatus": actual_timer_status,
        "result": result,
        "actual_duration": actual_duration,
        "actual_open_torque": actual_open_torque,
        "actual_close_torque": actual_close_torque,
        "result_value": result_value1,
        "actual_bubbles": actual_bubble,
        "actual_clamping_psr": actual_clamping_psr,
    }


def get_sync_live_pressure_data2(request, id, valve_serial_no, stationNum):

    s2_actual_pre = None
    s2_actual_timer_status = None
    s2_actual_time = None
    s2_result = None

    with connection.cursor() as cursor:
        print(f"[Station 2 Live] Querying with TEST_ID={id}, VALVE_SERIAL_NO={valve_serial_no}")

        if int(id) == 0:
            cursor.execute("""
                SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
                FROM current_status_station2
                WHERE VALVE_SERIAL_NO = %s
                ORDER BY id DESC
                LIMIT 1
            """, [valve_serial_no])
            print(f"[Station 2 Live] Using query without TEST_ID")
        else:
            cursor.execute("""
                SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
                FROM current_status_station2
                WHERE TEST_ID = %s AND VALVE_SERIAL_NO = %s
                ORDER BY id DESC
                LIMIT 1
            """, [id, valve_serial_no])
            print(f"[Station 2 Live] Using query with TEST_ID={id}")

        value2 = cursor.fetchone()
        
        if value2:
            print(f"[Station 2 Live] Data found: PRESSURE={value2[0]}, TIMER_STATUS={value2[1]}, DATE_TIME={value2[2]}, RESULT={value2[3]}")
        else:
            print(f"[Station 2 Live] WARNING: No data found in current_status_station2 for TEST_ID={id}, VALVE_SERIAL_NO={valve_serial_no}")

        s2_actual_duration = getstatus(HmiAddress.S2_ACTUAL_TEST_TIME)
        s2_actual_open_torque = getstatus(HmiAddress.S2_ACTUAL_OPEN_TORQUE)
        s2_actual_close_torque =getstatus(HmiAddress.S2_ACTUAL_CLOSE_TORQUE )
        s2_actual_bubble = getstatus(HmiAddress.S2_ACTUAL_BUBBLE_COUNT)
        s2_actual_clamping_psr=getstatus(HmiAddress.S2_ACTUAL_CALMPING_PRESSURE)
        result_value2 = getstatus(HmiAddress.S2_TEST_RESULT)
        # leak_pressure = getstatus(HmiAddress.)

        if value2:
            s2_actual_pre = value2[0]
            s2_actual_timer_status = value2[1]
            s2_actual_time = value2[2]
            s2_result = value2[3]

    result_data = {
        "connected": True,
        "current_pressure": float(s2_actual_pre) if s2_actual_pre is not None else 0.0,
        "timestamp": str(s2_actual_time) if s2_actual_time else "",
        "timerStatus": s2_actual_timer_status,
        "result": s2_result,
        "actual_duration": s2_actual_duration,
        "actual_open_torque": s2_actual_open_torque,
        "actual_close_torque": s2_actual_close_torque,
        "actual_bubbles": s2_actual_bubble,
        "actual_clamping_psr": s2_actual_clamping_psr,
        "result_value": result_value2
    }
    
    print(f"[Station 2 Live] Returning current_pressure={result_data['current_pressure']}")
    
    return result_data





def get_history_values(request, stationNum, testId, valve_serial_no):
    if stationNum not in [1, 2]:
        return JsonResponse({"error": "Invalid station"})

    if stationNum == 1:
        data =  get_history_prssure_data1(request, testId, valve_serial_no, stationNum)
    else:
        data = get_history_prssure_data2(request, testId, valve_serial_no, stationNum)

    return JsonResponse({
        "status": "success",
        "station": stationNum,
        "data": data
    })

#=============================== Get Histroy values on page load fro selected test id =====================================#


def get_sync_history_values(request, stationNum, testId, valve_serial_no):
    if stationNum not in [1, 2]:
        return JsonResponse({"error": "Invalid station"})

    if stationNum == 1:
        data = get_history_prssure_data1(request, testId, valve_serial_no, stationNum)
    else:
        data = get_history_prssure_data2(request, testId, valve_serial_no, stationNum)

    return JsonResponse({
        "status": "success",
        "station": stationNum,
        "data": data
    })

def get_history_prssure_data1(request, testId, valve_serial_no, stationId):


    with connection.cursor() as cursor:

        cursor.execute("""
        SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
        FROM current_status_station1
        WHERE TEST_ID = %s AND VALVE_SERIAL_NO = %s
        ORDER BY id ASC
    """, [testId, valve_serial_no])

        rows = cursor.fetchall() or []

    data = []
    for pressure, timer_status, date_time, result in rows:
        data.append({
            "pressure": float(pressure) if pressure is not None else 0.0,
            "timerStatus": timer_status,
            # "time": date_time.strftime("%H:%M:%S") if date_time else "",
            "time": date_time if date_time else "",
            "result": result
        })

    return data
    



def get_history_prssure_data2(request, testId, valve_serial_no, stationNum):


    with connection.cursor() as cursor:

        cursor.execute("""
        SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
        FROM current_status_station2
        WHERE TEST_ID = %s AND VALVE_SERIAL_NO = %s
        ORDER BY id ASC
    """, [testId, valve_serial_no])

        rows2 = cursor.fetchall() or []

    data = []
    for pressure, timer_status, date_time, result in rows2:
        data.append({
            "pressure": float(pressure) if pressure is not None else 0.0,
            "timerStatus": timer_status,
            # "time": date_time.strftime("%H:%M:%S") if date_time else "",
            "time": date_time if date_time else "",
            "result": result
        })

    return data



#=================================================================================================================#



@csrf_exempt
def test_result_status(request, stationNum, valve_serial_no):
    """Get test result status for button color coding"""
    
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    try:
        stationNum = int(stationNum)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TEST_ID, TEST_NAME, STATUS, VALVE_STATUS
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
            """, [valve_serial_no])
            
            rows = cursor.fetchall()
            
            test_statuses = {}
            for row in rows:
                test_id = row[0]
                test_name = row[1]
                status = row[2]  # 1 = PASS, 0 = FAIL, NULL = Not completed
                valve_status = row[3]  # "PASS" or "FAIL"
                
                test_statuses[test_id] = {
                    "testName": test_name,  # Changed from "test_name" to "testName" for frontend compatibility
                    "status": status,
                    "valve_status": valve_status,
                    "completed": valve_status is not None  # Has result
                }
            
            return JsonResponse({
                "status": "success",
                "station": stationNum,
                "test_statuses": test_statuses
            })
            
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


#=========================================Delete and Retest Funtion===============================================#
@csrf_exempt
def delete_and_retest(request, stationNum, testId, valve_serial_no):

    if request.method != "DELETE":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        stationNum = int(stationNum)
        testId = int(testId)

        # Choose table based on station
        if stationNum == 1:
            table = "current_status_station1"
        elif stationNum == 2:
            table = "current_status_station2"
        else:
            return JsonResponse(
                {"error": "Invalid station number"},
                status=400
            )

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE TEST_ID = %s
                    AND VALVE_SERIAL_NO = %s
                    """,
                    [testId, valve_serial_no]
                )
                
                cursor.execute(
                    """
                    UPDATE temp_pressure_analysis
                    SET 
                        STATUS = '2',
                        VALVE_STATUS = 'No'
                    WHERE TEST_ID = %s
                    AND VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                    """,
                    [testId, valve_serial_no]
                )
                
        
            return JsonResponse({
                "success": True,
                "message": "Previous test data deleted successfully",
                "station": stationNum,
                "testId": testId,
                "valve_serial_no": valve_serial_no
            })

    except ValueError:
        return JsonResponse(
            {"error": "Invalid station or test ID"},
            status=400
        )

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


#===================================================================================================================#

#=========================================Save final tested values function===============================================#

@csrf_exempt
def save_tested_values(request, testId, valve_serial_no, stationNum):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        stationNum = int(stationNum)

        body = json.loads(request.body.decode("utf-8"))
        print("received body", body)

        start_pressure = body.get("start_pressure")
        end_pressure   = body.get("end_pressure")
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        result_psr = body.get("result_psr")
        actual_time = body.get("actual_dur")
        clampping_psr = body.get("clamping_psr")
        open_torque = body.get("open_torque")
        close_torque = body.get("close_torque")
        pressure_drop = body.get("pressure_drop")
        test_result = body.get("test_result")

        # Convert test_result to status: 1 for PASS, 0 for FAIL
        status = 1 if test_result == "PASS" else 0


        if start_pressure is None or end_pressure is None:
            return JsonResponse({"error": "Missing pressure values"},status=400)
        
        # Prepare test data dictionary
        test_data = {
            'start_pressure': start_pressure,
            'end_pressure': end_pressure,
            'start_time': start_time,
            'end_time': end_time,
            'result_psr': result_psr,
            'actual_time': actual_time,
            'clamping_psr': clampping_psr,
            'open_torque': open_torque,
            'close_torque': close_torque,
            'pressure_drop': pressure_drop,
            'test_result': test_result,
            'status': status
        }
        
        # Call the service function to handle database updates
        update_tested_values_service(station_num=stationNum, test_id=testId, valve_serial_no=valve_serial_no, test_data=test_data)
        
        return JsonResponse({
            "status": "success",
            "message": "Final pressure saved"
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
    

#==============================================================Internal abrs push=====================================================#


def internal_abrs_push(valve_serial_no, testId):

    TEST_PAIR_MAPPING = {
        1: (4, 5),
        2: (6, 7),
        3: (8, 9),
        4: (10, 11),
        5: (12, 13),
    }

    COLUMN_MAPPING = {
        1:'COL1_VALUE',
        2:'COL2_VALUE',
        3:'COL3_VALUE',
        4:'COL4_VALUE',
        5:'COL5_VALUE',
        6:'COL6_VALUE',
        7:'COL7_VALUE',
        8:'COL8_VALUE',
        9:'COL9_VALUE',
        10:'COL10_VALUE',
        11:'COL11_VALUE',
        12:'COL12_VALUE',
        13:'COL13_VALUE'
    }

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT ACTUAL_OPEN_TORQUE, ACTUAL_CLOSE_TORQUE 
            FROM pressure_analysis
            WHERE VALVE_SER_NO = %s
            and CYCLE_COMPLETE = 'No'
        """, [valve_serial_no])

        torque_row = cursor.fetchone()
        if torque_row:
            open_torque, close_torque = torque_row

            cursor.execute("""
                UPDATE abrs_result_status
                SET COL1_VALUE = %s,
                    COL2_VALUE = %s
                WHERE SERIAL_NO = %s
            """, [open_torque, close_torque, valve_serial_no])


        if testId not in TEST_PAIR_MAPPING:
            return {"success": False, "local":False, "message": "No test data"}

        result_id, duration_id = TEST_PAIR_MAPPING[testId]
        result_col = COLUMN_MAPPING[result_id]
        duration_col = COLUMN_MAPPING[duration_id]

        cursor.execute("""
            SELECT result_pressure, actual_time
            FROM pressure_analysis
            WHERE VALVE_SER_NO = %s
            AND TEST_ID = %s
            AND CYCLE_COMPLETE = 'No'
        """, [valve_serial_no, testId])

        row = cursor.fetchone()
        if not row:
            return {"success": False, "local": False, "message": "No test data"}

        result_value, duration_value = row

        cursor.execute(f"""
            UPDATE abrs_result_status
            SET `{result_col}` = %s,
                `{duration_col}` = %s,
                STATUS = '2'
            WHERE SERIAL_NO = %s
        """, [result_value, duration_value, valve_serial_no])

    return {"success": True, "local": True, "message": "Pushed Successfully in Local"}

    
#===========================================================External abrs push========================================================#
def external_abrs_push(serial_no, assembly_no):
    print("[ABRS] Push started")


    # Check ABRS connection
    try:
        if not abrs_db.test_connection():
            print("[ABRS] Database connection failed: test_connection returned False")
            return {"success": False, "message": "ABRS connection failed"}
    except Exception as e:
        print("[ABRS] Database connection error:", e)
        return {"success": False, "message": "ABRS connection failed"}

    try:
        # ---- Push to ABRS (external system) ----
        ABRSService.push_data_to_abrs(serial_no, assembly_no)
        print("[ABRS] Push success")

    except Exception as e:
        print("[ABRS] Push failed:", e)
        return {"success": False, "message": "ABRS push failed"}

    # ---- Update local DB ONLY after successful push ----
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE abrs_result_status
                SET STATUS = '3'
                WHERE SERIAL_NO = %s
            """, [serial_no])
    except Exception as e:
        print("[DB] Failed to update ABRS status:", e)
        # ABRS push already succeeded, so still return success
        return {"success": True, "message": "Pushed to ABRS, but local status update failed"}

    return {"success": True, "message": "Data saved locally & pushed to ABRS successfully"}




#====================================CYCLE COMPLETE FUCTION=======================================================#
@csrf_exempt
def cycle_complete(request):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        # Get enabled station IDs and valve serial numbers from database
        with connection.cursor() as cursor:
            cursor.execute("SELECT ID, VALVE_SER_NO FROM master_temp_data WHERE STATION_STATUS='Enabled'")
            enabled_stations = cursor.fetchall()
        
        # Extract station IDs and create a mapping of station_id to valve_serial_no
        station_ids = []
        station_valve_map = {}
        
        for row in enabled_stations:
            station_id = row[0]
            valve_serial = row[1]
            station_ids.append(station_id)
            station_valve_map[station_id] = valve_serial
        
        print(f"Enabled stations from DB: {station_ids}")
        print(f"Station-Valve mapping: {station_valve_map}")
        
        if not station_ids:
            return JsonResponse({"status": "error", "message": "No enabled stations found"}, status=400)
        
        # Determine if both stations are enabled
        has_station1 = 1 in station_ids
        has_station2 = 2 in station_ids
        
        # Clear Station 1 if enabled
        if has_station1:
            valve_serial_s1 = station_valve_map.get(1)
            #Fetch ALL pending tests BEFORE marking cycle complete
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT TEST_ID
                    FROM pressure_analysis
                    WHERE VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [valve_serial_s1])

                test_rows = cursor.fetchall()

                #Push each test to ABRS
                for (test_id,) in test_rows:
                    internal_abrs_push(valve_serial_s1, test_id)

                # Update STATUS to 0 for all tests when cycle completes
                cursor.execute("""
                    UPDATE temp_pressure_analysis
                    SET STATUS = 0
                    WHERE VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [valve_serial_s1])

            print(f"Completing cycle for Station 1 with valve serial: {valve_serial_s1}")
            write_to_hmi(HmiAddress.S1_E_D_STATUS, 0)
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
            write_to_hmi(HmiAddress.S1_HIM_TEST_TYPE, 0)
            stop_station1()
            disable_sync_station1()

            if valve_serial_s1:
                cycle_complete_status(valve_serial_s1)
                clear_temp_pressure_analysis(valve_serial_s1)
                clear_testing_dataS1(valve_serial_s1)
            clear_station_1()
        
        # Clear Station 2 if enabled
        if has_station2:
            valve_serial_s2 = station_valve_map.get(2)

             #Fetch ALL pending tests BEFORE marking cycle complete
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT TEST_ID
                    FROM pressure_analysis
                    WHERE VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [valve_serial_s2])

                test_rows = cursor.fetchall()

                #Push each test to ABRS
                for (test_id,) in test_rows:
                    internal_abrs_push(valve_serial_s2, test_id)

                # Update STATUS to 0 for all tests when cycle completes
                cursor.execute("""
                    UPDATE temp_pressure_analysis
                    SET STATUS = 0
                    WHERE VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [valve_serial_s2])

            print(f"Completing cycle for Station 2 with valve serial: {valve_serial_s2}")
            write_to_hmi(HmiAddress.S2_E_D_STATUS, 0)
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
            write_to_hmi(HmiAddress.S2_HIM_TEST_TYPE, 0)
            stop_station2()
            disable_sync_station2()
            if valve_serial_s2:
                cycle_complete_status(valve_serial_s2)
                clear_temp_pressure_analysis(valve_serial_s2)
                clear_testing_dataS2(valve_serial_s2)
            clear_station_2()


        # ---------- STEP 2: ABRS PUSH ----------
        # Track ABRS push results
        internal_success = True
        external_success = True
        abrs_messages = []
        
        # Push to ABRS for each enabled station
        for station_id in station_ids:
            valve_serial = station_valve_map.get(station_id)
            if valve_serial:
                # Get assembly number for external push
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT ASSEMBLY_NO
                        FROM abrs_result_status
                        WHERE SERIAL_NO = %s
                    """, [valve_serial])

                    row = cursor.fetchone()

                if row:
                    # External ABRS push
                    external_response = external_abrs_push(valve_serial, row[0])
                    print(f"External ABRS push for Station {station_id}: {external_response}")
                    
                    # Track external push status
                    if not external_response.get("success", False):
                        external_success = False
                        abrs_messages.append(f"Station {station_id}: {external_response.get('message', 'External ABRS push failed')}")
                    else:
                        abrs_messages.append(f"Station {station_id}: {external_response.get('message', 'Pushed successfully')}")
                else:
                    external_success = False
                    abrs_messages.append(f"Station {station_id}: No assembly number found")
                    print(f"Warning: No assembly number found for Station {station_id} valve {valve_serial}")
        
        # Prepare response message based on ABRS push results
        if has_station1 and has_station2:
            base_message = "Both stations cycle completed"
        elif has_station1:
            base_message = "Station 1 cycle completed"
        elif has_station2:
            base_message = "Station 2 cycle completed"
        else:
            base_message = "Cycle completed"
        
        # Determine final message based on internal and external push status
        if internal_success and external_success:
            final_message = f"{base_message}. Data saved locally and pushed to ABRS successfully."
            abrs_status = "both_success"
        elif internal_success and not external_success:
            final_message = f"{base_message}. Data saved locally. {' '.join(abrs_messages)}"
            abrs_status = "internal_only"
        else:
            final_message = f"{base_message}. Warning: Some operations failed."
            abrs_status = "failed"
        
        return JsonResponse({
            "status": "success",
            "success": True,
            "message": final_message,
            "abrs_status": abrs_status,
            "internal_success": internal_success,
            "external_success": external_success,
            "cleared_stations": station_ids,
            "details": abrs_messages
        })

    except Exception as e:
        print(f"Error in cycle_complete: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "success": False, "message": str(e)}, status=500)


import json
from django.db import connection, transaction
from django.http import JsonResponse
from datetime import datetime
import time
from django.views.decorators.csrf import csrf_exempt
import threading, os
from openpyxl import Workbook
from io import BytesIO
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx, abrs_db
from bray_app.services.abrs_service import ABRSService
from bray_app.src import HmiAddress
from bray_app.views.api.generate_report_views import (
    export_station_data,
    excel_report,
    merged_report
)

from bray_app.services.syncpage_service import( 
    disable_sync_station1,
    disable_sync_station2,
    save_test_pressure_station1,
    save_test_pressure_station2,
    save_valve_serial_no,
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
    # both_auto = None
    
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
    s1_cycle_start_stop = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)
    s2_cycle_start_stop = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS)

    response = {
        "station_enabled": True,
        "machine_mode": 0,  # Both in auto
        "test_id": None,
        "cycle_complete": False,
        "test_changed": False,
        "both_stations": True
    }

    # CYCLE COMPLETE - check both stations
    if s1_cycle_start_stop == 0 and s2_cycle_start_stop == 0:  # cycle stopped
        if s1_hmi_test_type == 0 and s2_hmi_test_type == 0:
            print("[AUTO][BOTH] Cycle stopped")
            response["cycle_complete"] = True
            # Reset test type registers for both stations
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
            return response

    # TEST CHANGE - synchronize across both stations
    if s1_cycle_start_stop == 1 and s2_cycle_start_stop == 1:
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
    s1_cycle_start_stop = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)

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
    if s1_cycle_start_stop == 0:  # cycle stopped
        if s1_hmi_test_type == 0:
            print("[AUTO][S1] Cycle stopped")
            response["cycle_complete"] = True
            # Reset test type register
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)

    # TEST CHANGE (outside cycle complete check)
    if s1_cycle_start_stop == 1 and s1_hmi_test_type != s1_test_type:
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
    s2_cycle_start_stop = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS)

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
    if s2_cycle_start_stop == 0:  # cycle stopped
        if s2_hmi_test_type == 0:
            print("[AUTO][S2] Cycle stopped")
            response["cycle_complete"] = True
            # Reset test type register
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)

    # TEST CHANGE (outside cycle complete check)
    if s2_cycle_start_stop == 1 and s2_hmi_test_type != s2_test_type:
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
                # Use JOIN to verify both stations have matching values (except VALVE_SER_NO)
                cursor.execute("""
                    SELECT 
                        s1.VALVE_SER_NO AS s1_valve_ser_no,
                        s2.VALVE_SER_NO AS s2_valve_ser_no,
                        s1.SIZE_NAME,
                        s1.CLASS_NAME,
                        s1.PRESSURE_UNIT,
                        s1.SHELL_MATERIAL_NAME,
                        s1.COL8_VALUE,
                        s1.STATION_STATUS,
                        -- Check if values match (except VALVE_SER_NO)
                        CASE 
                            WHEN s1.SIZE_NAME = s2.SIZE_NAME 
                                AND s1.CLASS_NAME = s2.CLASS_NAME 
                                AND s1.PRESSURE_UNIT = s2.PRESSURE_UNIT 
                                AND s1.SHELL_MATERIAL_NAME = s2.SHELL_MATERIAL_NAME 
                                AND s1.COL8_VALUE = s2.COL8_VALUE 
                                AND s1.STATION_STATUS = s2.STATION_STATUS 
                            THEN 1 
                            ELSE 0 
                        END AS values_match
                    FROM master_temp_data s1
                    INNER JOIN master_temp_data s2 ON s1.id = 1 AND s2.id = 2
                    WHERE s1.id = 1
                """)
                result = cursor.fetchone()
                
                if result:
                    s1_valve_ser_no = result[0]
                    s2_valve_ser_no = result[1]
                    size_name = result[2]
                    class_name = result[3]
                    pressure_unit = result[4]
                    shell_material_name = result[5]
                    col8_value = result[6]
                    station_status = result[7]
                    values_match = result[8]
                    
                    # Check if values match
                    if values_match != 1:
                        return JsonResponse({
                            "status": "error", 
                            "message": "Station 1 and Station 2 have different values. Both stations must have matching SIZE, CLASS, PRESSURE_UNIT, MATERIAL, and STATUS."
                        })
                    
                    # Get torque values from HMI for both stations
                    s1_open_deg = getstatus(HmiAddress.S1_SET_OPEN_DEGREE)
                    s1_close_deg = getstatus(HmiAddress.S1_SET_CLOSE_DEGREE)
                    s2_open_deg = getstatus(HmiAddress.S2_SET_OPEN_DEGREE)
                    s2_close_deg = getstatus(HmiAddress.S2_SET_CLOSE_DEGREE)
                    s1_clamping_method = getstatus(HmiAddress.S1_CLAMPING_METHOD)
                    s2_clamping_method = getstatus(HmiAddress.S2_CLAMPING_METHOD)
                    
                    if s1_clamping_method == 1 and s2_clamping_method == 1:
                        both_clamping_method = "Control Clamping"
                    elif s1_clamping_method== 0 and s2_clamping_method== 0 :
                        both_clamping_method = "Proportional Clamping"
                    else:
                        both_clamping_method = "Unknown"

                    print("set torque values", s1_open_deg, s1_close_deg, s2_open_deg, s2_close_deg)
                    
                    # Build response with common values and separate valve serial numbers
                    both_data = {
                        "status": "success",
                        "station_id": "both",
                        "s1_valve_serial_no": s1_valve_ser_no,
                        "s2_valve_serial_no": s2_valve_ser_no,
                        "size": size_name,
                        "class": class_name,
                        "pressure_unit": pressure_unit,
                        "body_material": shell_material_name,
                        # "assembled_by": col8_value,
                        "tested_by": col8_value,
                        "s1_open_degree": s1_open_deg,
                        "s1_close_degree": s1_close_deg,
                        "s2_open_degree": s2_open_deg,
                        "s2_close_degree": s2_close_deg,
                        "clamping_method": both_clamping_method
                    }

                    # Get valve size ID
                    cursor.execute("""
                        SELECT SIZE_ID, SIZE_NAME  
                        FROM valvesize
                        WHERE SIZE_NAME = %s
                        """, [size_name])
                    v_size = cursor.fetchone()  

                    if v_size:
                        size_id = v_size[0]     
                        write_to_hmi(HmiAddress.S1_VALVE_SIZE, size_id)
                        write_to_hmi(HmiAddress.S2_VALVE_SIZE, size_id)

                    # Write to HMI for station 1
                    write_to_hmi(HmiAddress.S1_VALVE_CLASS, class_name)
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, pressure_unit)
                    write_to_hmi(HmiAddress.S1_E_D_STATUS, 1 if station_status == "Enabled" else 0)
                    
                    # Write to HMI for station 2
                    write_to_hmi(HmiAddress.S2_VALVE_CLASS, class_name)
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, pressure_unit)
                    write_to_hmi(HmiAddress.S2_E_D_STATUS, 1 if station_status == "Enabled" else 0)

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
                    s1_open_deg = getstatus(HmiAddress.S1_SET_OPEN_DEGREE)
                    s1_close_deg = getstatus(HmiAddress.S1_SET_CLOSE_DEGREE)
                    
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
                        "open_degree": s1_open_deg,
                        "close_degree": s1_close_deg
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

                    write_to_hmi(HmiAddress.S1_VALVE_CLASS, class_name)
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
                    s2_open_deg = getstatus(HmiAddress.S2_SET_OPEN_DEGREE)
                    s2_close_deg = getstatus(HmiAddress.S2_SET_CLOSE_DEGREE)
                    
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
                        "open_degree": s2_open_deg,
                        "close_degree": s2_close_deg
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

                    write_to_hmi(HmiAddress.S2_VALVE_CLASS, class_name2)
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
    print("sync enabled test buttons fetch values for stationid",  stationId)
    try:
        with connection.cursor() as cursor:
            # Determine which table to query based on station_id
            if stationId == 'both':
                # For both stations, use JOIN to get matching tests from both stations
                cursor.execute("""
                    SELECT s1.TEST_ID, s1.VALVE_SERIAL_NO, s1.TEST_NAME, s1.TESTING_PR_UNIT, s1.TESTING_DUR_UNIT 
                    FROM temp_testing_data_s1 s1
                    INNER JOIN temp_testing_data_s2 s2 
                        ON s1.TEST_ID = s2.TEST_ID 
                        AND s1.TEST_NAME = s2.TEST_NAME
                """)
                test_buttons = cursor.fetchall()

                # Map test_id to HMI addresses for both stations
                # TEST_ID mapping to HMI addresses:
                # 1 = HYDRO_SHELL, 2 = HYDRO_SEAT_P, 3 = HYDRO_SEAT_N, 4 = AIR_SEAT_P, 5 = AIR_SEAT_N
                test_id_to_hmi_map = {
                    1: (HmiAddress.S1_HYDRO_SHELL_E_D_STATUS, HmiAddress.S2_HYDRO_SHELL_E_D_STATUS),
                    2: (HmiAddress.S1_HYDRO_SEAT_P_E_D_STATUS, HmiAddress.S2_HYDRO_SEAT_P_E_D_STATUS),
                    3: (HmiAddress.S1_HYDRO_SEAT_N_E_D_STATUS, HmiAddress.S2_HYDRO_SEAT_N_E_D_STATUS),
                    4: (HmiAddress.S1_AIR_SEAT_P_E_D_STATUS, HmiAddress.S2_AIR_SEAT_P_E_D_STATUS),
                    5: (HmiAddress.S1_AIR_SEAT_N_E_D_STATUS, HmiAddress.S2_AIR_SEAT_N_E_D_STATUS),
                }

                # Write to HMI for each matching test
                for btn in test_buttons:
                    test_id = btn[0]
                    if test_id in test_id_to_hmi_map:
                        s1_hmi_addr, s2_hmi_addr = test_id_to_hmi_map[test_id]
                        write_to_hmi(s1_hmi_addr, 1)
                        write_to_hmi(s2_hmi_addr, 1)
                
            elif stationId == '1':
                # For station 1, get station 1 buttons
                cursor.execute("""
                    SELECT TEST_ID, VALVE_SERIAL_NO, TEST_NAME, TESTING_PR_UNIT, TESTING_DUR_UNIT 
                    FROM temp_testing_data_s1
                """)
                test_buttons = cursor.fetchall()

                write_to_hmi(HmiAddress.S1_HYDRO_SHELL_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S1_HYDRO_SEAT_P_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S1_HYDRO_SEAT_N_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S1_AIR_SEAT_P_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S1_AIR_SEAT_N_E_D_STATUS, 1)
                
            elif stationId == '2':
                # For station 2, get station 2 buttons
                cursor.execute("""
                    SELECT TEST_ID, VALVE_SERIAL_NO, TEST_NAME, TESTING_PR_UNIT, TESTING_DUR_UNIT 
                    FROM temp_testing_data_s2
                """)
                test_buttons = cursor.fetchall()

                write_to_hmi(HmiAddress.S2_HYDRO_SHELL_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S2_HYDRO_SEAT_P_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S2_HYDRO_SEAT_N_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S2_AIR_SEAT_P_E_D_STATUS, 1)
                write_to_hmi(HmiAddress.S2_AIR_SEAT_N_E_D_STATUS, 1)
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
            start_sync_station_threads(station1_enabled=True, station2_enabled=True)
            
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
            start_sync_station_threads(station1_enabled=True, station2_enabled=False)
            return response
        
        # Handle station 2
        elif stationId == "2" or stationId == 2:
            print("Station ID is 2")
            response = set_pressure_station2(id, name, valve_serial_no, psr_unit)
            # Start thread for station 2 after setting pressure
            start_sync_station_threads(station1_enabled=False, station2_enabled=True)
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




def _set_pressure_for_station(station_num, id, name, valve_serial_no, psr_unit):
    """
    Unified helper function to set pressure values for any station.
    Eliminates code duplication and optimizes database queries.
    
    Args:
        station_num: Station number (1 or 2)
        id: Test ID
        name: Test name
        valve_serial_no: Valve serial number
        psr_unit: Pressure unit (BAR, PSI, or KG)
    
    Returns:
        tuple: (station_data dict, final_data dict, cursor)
    """
    # Station-specific configuration
    STATION_CONFIG = {
        1: {
            'table': 'temp_testing_data_s1',
            'hmi_addresses': {
                'bubble': HmiAddress.S1_SET_BUBBLE_COUNT,
                'clamping': HmiAddress.S1_SET_CLAMPING_PRESSURE,
                'set_pressure': HmiAddress.S1_SET_PRESSURE,
                'set_time': HmiAddress.S1_SET_TEST_TIME,
                'valve_class': HmiAddress.S1_VALVE_CLASS,
                'test_type': HmiAddress.S1_TEST_TYPE,
            },
            'save_function': save_test_pressure_station1
        },
        2: {
            'table': 'temp_testing_data_s2',
            'hmi_addresses': {
                'bubble': HmiAddress.S2_SET_BUBBLE_COUNT,
                'clamping': HmiAddress.S2_SET_CLAMPING_PRESSURE,
                'set_pressure': HmiAddress.S2_SET_PRESSURE,
                'set_time': HmiAddress.S2_SET_TEST_TIME,
                'valve_class': HmiAddress.S2_VALVE_CLASS,
                'test_type': HmiAddress.S2_TEST_TYPE,
            },
            'save_function': save_test_pressure_station2
        }
    }
    
    # Validate pressure unit and map to column name (prevents SQL injection)
    PRESSURE_COLUMN_MAP = {
        'BAR': 'TESTING_PR_BAR',
        'PSI': 'TESTING_PR_PSI',
        'KG': 'TESTING_PR_KG'
    }
    
    if psr_unit not in PRESSURE_COLUMN_MAP:
        raise ValueError(f"Invalid pressure unit: {psr_unit}. Must be one of: {', '.join(PRESSURE_COLUMN_MAP.keys())}")
    
    column_name = PRESSURE_COLUMN_MAP[psr_unit]
    config = STATION_CONFIG[station_num]
    hmi = config['hmi_addresses']
    
    # Get HMI values
    set_bubble_count = getstatus(hmi['bubble'])
    set_clampping_psr = getstatus(hmi['clamping'])
    
    with connection.cursor() as cursor:
        #Use JOIN to fetch all data in ONE query 
        optimized_query = f"""
            SELECT 
                t.VALVE_SERIAL_NO, t.TEST_ID, t.TEST_NAME, t.TEST_MEDIUM,
                t.TEST_CATEGORY, t.TESTING_PR_UNIT, t.{column_name}, 
                t.TESTING_DUR_UNIT, t.TESTING_DUR_SEC,
                m.CLASS_NAME, v.CLASS_ID
            FROM {config['table']} t
            LEFT JOIN master_temp_data m ON t.VALVE_SERIAL_NO = m.VALVE_SER_NO
            LEFT JOIN valveclass v ON m.CLASS_NAME = v.CLASS_NAME
            WHERE t.TEST_ID = %s AND t.TEST_NAME = %s
        """
        
        cursor.execute(optimized_query, [id, name])
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"No test data found for Station {station_num} with TEST_ID={id} and TEST_NAME={name}")
        
        # Extract data from the single query result
        valve_serial_no_db = result[0]
        test_id = result[1]
        test_name = result[2]
        pressure_unit = result[5]
        set_pressure = result[6]
        dur_unit = result[7]
        set_duration = result[8]
        class_name = result[9]
        class_id = result[10]
        
        if not class_id:
            raise ValueError(f"No valve class found for valve serial number: {valve_serial_no}")
        
        # Build station data dictionary
        station_data = {
            "VALVE_SERIAL_NO": valve_serial_no_db,
            "TEST_ID": test_id,
            "TEST_NAME": test_name,
            "TESTING_PSR_UNIT": pressure_unit,
            "TESTING_PRESSURE": set_pressure,
            "TESTING_DUR_UNIT": dur_unit,
            "TESTING_DUR": set_duration,
            "set_clampping_psr": set_clampping_psr,
            "set_bubble_count": set_bubble_count
        }
        
        print(f"Station {station_num} - Class: {class_name}, Class ID: {class_id}")
        
        # Write to HMI
        write_to_hmi(hmi['set_pressure'], int(set_pressure))
        write_to_hmi(hmi['set_time'], int(set_duration))
        write_to_hmi(hmi['valve_class'], int(class_id))
        
        # Map pressure unit to HMI code
        pressure_unit_map = {
            'psi': 1,
            'bar': 2,
            'kg/cm2g': 3,
            'kg': 3  # Assuming KG maps to kg/cm2g
        }
        unit_code = pressure_unit_map.get(pressure_unit.lower(), 3)
        write_to_hmi(HmiAddress.PRESSURE_UNIT, unit_code)
        
        write_to_hmi(hmi['test_type'], int(test_id))
        
        # Fetch master data with all columns
        master_query = """
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
            raise ValueError(f"No master data found for valve serial number: {valve_serial_no}")
        
        # Build master data dictionary
        columns = [col[0] for col in cursor.description]
        data = dict(zip(columns, master_data))
        
        # Extract parameters (COL1-COL24)
        parameters = {}
        for i in range(1, 25):
            col_name = data.get(f"COL{i}_NAME")
            value = data.get(f"COL{i}_VALUE")
            if col_name:  # ignore empty/null columns
                parameters[col_name] = value
        
        final_data = {
            "STANDARD_NAME": data["STANDARD_NAME"],
            "SIZE_NAME": data["SIZE_NAME"],
            "TYPE_NAME": data["TYPE_NAME"],
            "CLASS_NAME": data["CLASS_NAME"],
            "SHELL_MATERIAL_NAME": data["SHELL_MATERIAL_NAME"],
            "PARAMETERS": parameters,
        }
        
        # Call station-specific save function
        config['save_function'](id, name, valve_serial_no, station_data, final_data, cursor)
        
        return station_data, final_data


def set_pressure_station1(id, name, valve_serial_no, psr_unit):
    """
    Set pressure values for station 1 and return test data.
    This is now a lightweight wrapper around the unified function.
    """
    try:
        print(f"set_pressure_station1: id={id}, name={name}, valve_serial_no={valve_serial_no}, psr_unit={psr_unit}")
        
        station_data1, final_data_1 = _set_pressure_for_station(
            station_num=1,
            id=id,
            name=name,
            valve_serial_no=valve_serial_no,
            psr_unit=psr_unit
        )
        
        return JsonResponse({
            "status": "success",
            "station": 1,
            "station1_value": station_data1
        }, safe=False)
    
    except ValueError as e:
        print(f"VALIDATION ERROR in set_pressure_station1: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    except Exception as e:
        print(f"ERROR in set_pressure_station1: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

        



def set_pressure_station2(id, name, valve_serial_no, psr_unit):
    """
    Set pressure values for station 2 and return test data.
    This is now a lightweight wrapper around the unified function.
    """
    try:
        print(f"set_pressure_station2: id={id}, name={name}, valve_serial_no={valve_serial_no}, psr_unit={psr_unit}")
        
        station2_data, final_data_2 = _set_pressure_for_station(
            station_num=2,
            id=id,
            name=name,
            valve_serial_no=valve_serial_no,
            psr_unit=psr_unit
        )
        
        return JsonResponse({
            "status": "success",
            "station": 2,
            "station2_value": station2_data
        }, safe=False)
    
    except ValueError as e:
        print(f"VALIDATION ERROR in set_pressure_station2: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    except Exception as e:
        print(f"ERROR in set_pressure_station2: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

#===============================================================================================================#


#================================Thread functions to start and stop threads  ===================================#

station1_thread = None
station2_thread = None
both_stations_thread = None

station1_stop = threading.Event()
station2_stop = threading.Event()
both_stations_stop = threading.Event()

# Global variables to track timer synchronization across both stations
controlling_timer_station = None  # Which station's timer is controlling (1 or 2)

def start_sync_station_threads(station1_enabled=False, station2_enabled=False):
    global station1_thread, station2_thread, both_stations_thread

    # Stop all threads first to ensure clean state
    stop_sync_station1()
    stop_sync_station2()
    stop_sync_both_stations()

    if station1_enabled and station2_enabled:
        # Start BOTH thread
        print("Starting BOTH stations thread...")
        both_stations_stop.clear()
        both_stations_thread = threading.Thread(
            target=store_sync_pressure_both,
            daemon=True
        )
        both_stations_thread.start()
        
    elif station1_enabled:
        # Start Station 1 thread
        print("Starting Station 1 thread...")
        station1_stop.clear()
        station1_thread = threading.Thread(
            target=store_sync_pressure_station1,
            daemon=True
        )
        station1_thread.start()

    elif station2_enabled:
        # Start Station 2 thread
        print("Starting Station 2 thread...")
        station2_stop.clear()
        station2_thread = threading.Thread(
            target=store_sync_pressure_station2,
            daemon=True
        )
        station2_thread.start()


def store_sync_pressure_both():
    """
    Handle data storage for BOTH stations simultaneously.
    Synchronizes timer status based on the first station to start.
    """
    global controlling_timer_station
    print("Both Stations pressure thread started")

    while not both_stations_stop.is_set():
        try:
            # 1. Check Timer Status
            s1_timer_status = getstatus(HmiAddress.S1_TIMER_STATUS)
            s2_timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)

            # 2. Determine Controlling Station
            if controlling_timer_station is None:
                if s1_timer_status == 1:
                    controlling_timer_station = 1
                    print("✓ S1 Timer Started first -> S1 Controlling")
                elif s2_timer_status == 1:
                    controlling_timer_station = 2
                    print("✓ S2 Timer Started first -> S2 Controlling")
            
            # 3. Determine Active Timer Status & Handle Reset
            active_timer_status = 0
            
            if controlling_timer_station == 1:
                active_timer_status = s1_timer_status
                # Reset control if timer stops
                if s1_timer_status == 0:
                    controlling_timer_station = None
                    print("✓ S1 Stopped -> Released Control")
                    
            elif controlling_timer_station == 2:
                active_timer_status = s2_timer_status
                # Reset control if timer stops
                if s2_timer_status == 0:
                    controlling_timer_station = None
                    print("✓ S2 Stopped -> Released Control")
            
            # 4. Fetch & Save Data for BOTH stations using active_timer_status
            with connection.cursor() as cursor:
                # --- STATION 1 DATA ---
                cursor.execute("""
                    SELECT VALVE_SER_NO, PRESSURE_UNIT, STATION_STATUS 
                    FROM master_temp_data WHERE ID = 1
                """)
                s1_row = cursor.fetchone()
                
                if s1_row:
                    s1_serial = s1_row[0]
                    s1_unit = s1_row[1].lower()
                    
                    # Get Pressure
                    if s1_unit == 'psi':
                        s1_pres = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                    elif s1_unit == 'bar':
                        s1_pres = getstatus(HmiAddress.S1_ACTUAL_PRESSURE) / 10
                    elif s1_unit == 'kg/cm2g':
                        s1_pres = getstatus(HmiAddress.S1_ACTUAL_PRESSURE) / 10
                    else:
                        s1_pres = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)

                    # Get Other Values
                    s1_result = getstatus(HmiAddress.S1_TEST_RESULT)
                    s1_test_id = getstatus(HmiAddress.S1_TEST_TYPE)
                    
                    # Get Test Name
                    cursor.execute("SELECT TEST_NAME FROM temp_testing_data_s1 WHERE TEST_ID = %s", [s1_test_id])
                    test_row = cursor.fetchone()
                    s1_test_name = test_row[0] if test_row else None
                    
                    # Insert S1
                    cursor.execute("""
                        INSERT INTO current_status_station1
                        (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [s1_serial, s1_test_id, s1_test_name, s1_pres, active_timer_status, s1_result])

                # --- STATION 2 DATA ---
                cursor.execute("""
                    SELECT VALVE_SER_NO, PRESSURE_UNIT, STATION_STATUS 
                    FROM master_temp_data WHERE ID = 2
                """)
                s2_row = cursor.fetchone()
                
                if s2_row:
                    s2_serial = s2_row[0]
                    s2_unit = s2_row[1].lower()
                    
                    # Get Pressure
                    if s2_unit == 'psi':
                        s2_pres = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                    elif s2_unit == 'bar':
                        s2_pres = getstatus(HmiAddress.S2_ACTUAL_PRESSURE) / 10
                    elif s2_unit == 'kg/cm2g':
                        s2_pres = getstatus(HmiAddress.S2_ACTUAL_PRESSURE) / 10
                    else:
                        s2_pres = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)

                    # Get Other Values
                    s2_result = getstatus(HmiAddress.S2_TEST_RESULT)
                    s2_test_id = getstatus(HmiAddress.S2_TEST_TYPE)
                    
                    # Get Test Name
                    cursor.execute("SELECT TEST_NAME FROM temp_testing_data_s2 WHERE TEST_ID = %s", [s2_test_id])
                    test_row = cursor.fetchone()
                    s2_test_name = test_row[0] if test_row else None
                    
                    # Insert S2 
                    cursor.execute("""
                        INSERT INTO current_status_station2
                        (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [s2_serial, s2_test_id, s2_test_name, s2_pres, active_timer_status, s2_result])

            # print(f"BOTH Thread: Timer={active_timer_status} (Controlled by S{controlling_timer_station if controlling_timer_station else 'None'})")

        except Exception as e:
            print(f"Error in store_pressure_both: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(1)


def store_sync_pressure_station1():
    """
    Handle data storage for STATION 1 ONLY.
    Independent timer logic.
    """
    print("Station-1 pressure thread started (Solo Mode)")

    while not station1_stop.is_set():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT VALVE_SER_NO, PRESSURE_UNIT 
                    FROM master_temp_data WHERE ID = 1
                """)
                row = cursor.fetchone()
                
                if row:
                    serial_no = row[0]
                    unit = row[1].lower()
                    
                    if unit == 'psi':
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                    elif unit == 'bar':
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE) / 10
                    elif unit == 'kg/cm2g':
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE) / 10
                    else:
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)

                    timer_status = getstatus(HmiAddress.S1_TIMER_STATUS)
                    result = getstatus(HmiAddress.S1_TEST_RESULT)
                    test_id = getstatus(HmiAddress.S1_TEST_TYPE)
                    
                    cursor.execute("SELECT TEST_NAME FROM temp_testing_data_s1 WHERE TEST_ID = %s", [test_id])
                    test_row = cursor.fetchone()
                    test_name = test_row[0] if test_row else None
                    
                    cursor.execute("""
                        INSERT INTO current_status_station1
                        (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [serial_no, test_id, test_name, pressure, timer_status, result])
                    
                    # print(f"S1 Thread: Timer={timer_status}")

        except Exception as e:
            print(f"Error in store_pressure_station1: {e}")
            
        time.sleep(1)


def store_sync_pressure_station2():
    """
    Handle data storage for STATION 2 ONLY.
    Independent timer logic.
    """
    print("Station-2 pressure thread started (Solo Mode)")

    while not station2_stop.is_set():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT VALVE_SER_NO, PRESSURE_UNIT 
                    FROM master_temp_data WHERE ID = 2
                """)
                row = cursor.fetchone()
                
                if row:
                    serial_no = row[0]
                    unit = row[1].lower()
                    
                    if unit == 'psi':
                        pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                    elif unit == 'bar':
                        pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE) / 10
                    elif unit == 'kg/cm2g':
                        pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE) / 10
                    else:
                        pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)

                    timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)
                    result = getstatus(HmiAddress.S2_TEST_RESULT)
                    test_id = getstatus(HmiAddress.S2_TEST_TYPE)
                    
                    cursor.execute("SELECT TEST_NAME FROM temp_testing_data_s2 WHERE TEST_ID = %s", [test_id])
                    test_row = cursor.fetchone()
                    test_name = test_row[0] if test_row else None
                    
                    cursor.execute("""
                        INSERT INTO current_status_station2
                        (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [serial_no, test_id, test_name, pressure, timer_status, result])
                    
                    # print(f"S2 Thread: Timer={timer_status}")

        except Exception as e:
            print(f"Error in store_pressure_station2: {e}")
            
        time.sleep(1)


def stop_sync_station1():
    global station1_thread
    if station1_thread and station1_thread.is_alive():
        station1_stop.set()
        station1_thread.join(timeout=2.0)
        station1_thread = None
        print("Stopped Station 1 Thread")

def stop_sync_station2():
    global station2_thread
    if station2_thread and station2_thread.is_alive():
        station2_stop.set()
        station2_thread.join(timeout=2.0)
        station2_thread = None
        print("Stopped Station 2 Thread")

def stop_sync_both_stations():
    global both_stations_thread
    if both_stations_thread and both_stations_thread.is_alive():
        both_stations_stop.set()
        both_stations_thread.join(timeout=2.0)
        both_stations_thread = None
        print("Stopped Both Stations Thread")


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
        actual_open_degree = getstatus(HmiAddress. S1_ACTUAL_OPEN_DEGREE)
        actual_close_degree = getstatus(HmiAddress. S1_ACTUAL_CLOSE_DEGREE)
        actual_open_torque = getstatus(HmiAddress.S1_ACTUAL_OPEN_TORQUE)
        actual_close_torque =getstatus(HmiAddress.S1_ACTUAL_CLOSE_TORQUE )
        result_value1 = getstatus(HmiAddress.S1_TEST_RESULT)
        actual_bubble = getstatus(HmiAddress.S1_ACTUAL_BUBBLE_COUNT)
        actual_clamping_psr=getstatus(HmiAddress.S1_ACTUAL_CALMPING_PRESSURE)
        # s1_alarm_msg= getstatus(HmiAddress.S1_ALARM_STATUS)
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
        "actual_open_degree": actual_open_degree,
        "actual_close_degree": actual_close_degree,
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
        s2_actual_open_degree = getstatus(HmiAddress.S2_ACTUAL_OPEN_DEGREE)
        s2_actual_close_degree = getstatus(HmiAddress.S2_ACTUAL_CLOSE_DEGREE)
        s2_actual_open_torque = getstatus(HmiAddress.S2_ACTUAL_OPEN_TORQUE)
        s2_actual_close_torque =getstatus(HmiAddress.S2_ACTUAL_CLOSE_TORQUE )
        s2_actual_bubble = getstatus(HmiAddress.S2_ACTUAL_BUBBLE_COUNT)
        s2_actual_clamping_psr=getstatus(HmiAddress.S2_ACTUAL_CALMPING_PRESSURE)
        # s2_alarm_msg = getstatus(HmiAddress.S2_ALARM_STATUS)
        result_value2 = getstatus(HmiAddress.S2_TEST_RESULT)

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
        "actual_open_degree": s2_actual_open_degree,
        "actual_close_degree": s2_actual_close_degree,
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
            "time": str(date_time) if date_time else "",
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
            "time": str(date_time) if date_time else "",
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

@csrf_exempt
def reset_all_station(request):
    """
    Reset all stations - clears test data and resets HMI registers.
    Only works in Auto mode for safety.
    """
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Invalid request method. Use POST."
        }, status=405)
    
    try:
        # Parse request body
        data = json.loads(request.body)
        mode = data.get('mode', '')
        
        # Verify we're in Auto mode
        if mode != "Auto":
            return JsonResponse({
                "status": "error",
                "message": "Reset is only available in Auto mode."
            }, status=400)
        
        # Double-check mode from HMI
        s1_machine_mode = getstatus(HmiAddress.S1_MACHINE_MODE)
        s2_machine_mode = getstatus(HmiAddress.S2_MACHINE_MODE)
        

        if s1_machine_mode != 0 and s2_machine_mode != 0:
            return JsonResponse({
                "status": "error",
                "message": "Both stations must be in Auto mode (0) to reset."
            }, status=400)
        
        print("[RESET] Starting validation checks before reset...")

        # Check 1: Verify timer status for both stations (must be 0)
        s1_timer_status = getstatus(HmiAddress.S1_TIMER_STATUS)
        s2_timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)

        if s1_timer_status != 0:
            return JsonResponse({
                "status": "warning",
                "message": "Station 1 timer is running. Please stop the timer before resetting."
            }, status=400)
        
        if s2_timer_status != 0:
            return JsonResponse({
                "status": "warning",
                "message": "Station 2 timer is running. Please stop the timer before resetting."
            }, status=400)

        # Check 2: Verify test cycle status (must be 0)
        s1_cycle_start_stop = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)
        s2_cycle_start_stop = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS)
        
        if s1_cycle_start_stop != 0 or s2_cycle_start_stop != 0:
            return JsonResponse({
                "status": "warning",
                "message": "Test cycle is in progress. Please stop the test cycle before resetting."
            }, status=400)
        
        # All checks passed - proceed with reset
        print("[RESET] All validation checks passed. Executing reset...")

        stop_sync_both_stations()
        stop_sync_station1()
        stop_sync_station2()
        clear_station_1()
        clear_station_2()
        
        # Reset HMI registers for both stations
        # Station 1
        write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
        write_to_hmi(HmiAddress.S1_HIM_TEST_TYPE, 0)
        write_to_hmi(HmiAddress.S1_SET_PRESSURE, 0)
        write_to_hmi(HmiAddress.S1_SET_TEST_TIME, 0)

        write_to_hmi(HmiAddress.S1_HYDRO_SHELL_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S1_HYDRO_SEAT_P_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S1_HYDRO_SEAT_N_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S1_AIR_SEAT_P_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S1_AIR_SEAT_N_TEST_STATUS, 0)
        
        # Station 2
        write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
        write_to_hmi(HmiAddress.S2_HIM_TEST_TYPE, 0)
        write_to_hmi(HmiAddress.S2_SET_PRESSURE, 0)
        write_to_hmi(HmiAddress.S2_SET_TEST_TIME, 0)

        write_to_hmi(HmiAddress.S2_HYDRO_SHELL_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S2_HYDRO_SEAT_P_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S2_HYDRO_SEAT_N_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S2_AIR_SEAT_P_TEST_STATUS, 0)
        write_to_hmi(HmiAddress.S2_AIR_SEAT_N_TEST_STATUS, 0)   
        
        # Reset test cycle
        # write_to_hmi(HmiAddress.TEST_CYCLE, 0)
        
        print("[RESET] Reset HMI registers for both stations")
        
        return JsonResponse({
            "status": "success",
            "message": f"All stations reset successfully.",
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON in request body."
        }, status=400)
    except Exception as e:
        print(f"[RESET ERROR] {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "status": "error",
            "message": f"Reset failed: {str(e)}"
        }, status=500)


#=========================================Save final tested values function===============================================#

@csrf_exempt
def save_tested_values(request, testId, valve_serial_no, stationNum):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        stationNum = int(stationNum)
        
        body = json.loads(request.body.decode("utf-8"))
        print("received body", body)

        if stationNum == 1:
            test_result= "PASS" if getstatus(HmiAddress.S1_TEST_RESULT) == 1 else "FAIL"
        if stationNum == 2:
            test_result= "PASS" if getstatus(HmiAddress.S2_TEST_RESULT) == 1 else "FAIL"

        # Convert test_result to status: 1 for PASS, 0 for FAIL
        status = 1 if test_result == "PASS" else 0

        # --- HMI STATUS WRITING LOGIC START ---
        # Map Test IDs to HMI Addresses
        if stationNum == 1:
            test_id_to_address = {
                1: HmiAddress.S1_HYDRO_SHELL_TEST_STATUS,
                2: HmiAddress.S1_HYDRO_SEAT_P_TEST_STATUS,
                3: HmiAddress.S1_HYDRO_SEAT_N_TEST_STATUS,
                4: HmiAddress.S1_AIR_SEAT_P_TEST_STATUS,
                5: HmiAddress.S1_AIR_SEAT_N_TEST_STATUS
            }
        else:  # stationNum == 2
            test_id_to_address = {
                1: HmiAddress.S2_HYDRO_SHELL_TEST_STATUS,
                2: HmiAddress.S2_HYDRO_SEAT_P_TEST_STATUS,
                3: HmiAddress.S2_HYDRO_SEAT_N_TEST_STATUS,
                4: HmiAddress.S2_AIR_SEAT_P_TEST_STATUS,
                5: HmiAddress.S2_AIR_SEAT_N_TEST_STATUS
            }

        # Write status to corresponding HMI address
        if testId in test_id_to_address:
            hmi_address = test_id_to_address[testId]
            try:
                write_to_hmi(hmi_address, status)
                print(f"Updated HMI Address {hmi_address} for Test ID {testId} with Status {status}")
            except Exception as e:
                print(f"Failed to update HMI status for Test ID {testId}: {str(e)}")
        else:
             print(f"Test ID {testId} not mapped to any HMI address for Station {stationNum}")
        # --- HMI STATUS WRITING LOGIC END ---

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
        test_result = test_result


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
            "message": "Final pressure saved",
            "result": test_result
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
    """
    Optimized cycle complete function for sync mode.
    Handles both stations with proper failure detection, conditional report generation,
    ABRS push logic, and count increment handling.
    
    Workflow:
    1. Validation (pressure drain, cycle status)
    2. Get enabled stations
    3. For each station:
       a. Check for failures
       b. Internal ABRS push (if no failures)
       c. Save data
       d. Generate reports (if no failures)
       e. Clear temp data
       f. Reset HMI
    4. External ABRS push
    5. Return response
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        # ========== STEP 1: VALIDATION ==========
        sync_pressure_drain_s1 = getstatus(HmiAddress.S1_PRESSURE_DRAIN)
        sync_pressure_drain_s2 = getstatus(HmiAddress.S2_PRESSURE_DRAIN)

        # Check if either station has pressure not drained
        if sync_pressure_drain_s1 != 0 or sync_pressure_drain_s2 != 0:
            if sync_pressure_drain_s1 != 0 and sync_pressure_drain_s2 != 0:
                message = "Pressure is not drained in both Station 1 and Station 2"
            elif sync_pressure_drain_s1 != 0:
                message = "Pressure is not drained in Station 1"
            else:
                message = "Pressure is not drained in Station 2"
            return JsonResponse({"status": "warning", "message": message}, status=400)

        s1_cycle_start_stop = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)
        s2_cycle_start_stop = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS) 

        if s1_cycle_start_stop != 0 or s2_cycle_start_stop != 0:
            if s1_cycle_start_stop != 0 and s2_cycle_start_stop != 0:
                message = "Cycle test is running in both stations"
            elif s1_cycle_start_stop != 0:
                message = "Cycle test is running in Station 1"
            else:
                message = "Cycle test is running in Station 2"
            return JsonResponse({"status": "warning", "message": message}, status=400)

        # ========== STEP 2: GET ENABLED STATIONS ==========
        with connection.cursor() as cursor:
            cursor.execute("SELECT ID, VALVE_SER_NO FROM master_temp_data WHERE STATION_STATUS='Enabled'")
            enabled_stations = cursor.fetchall()
        
        station_ids = []
        station_valve_map = {}
        station_failure_map = {}  # Track failures per station
        
        for row in enabled_stations:
            station_id = row[0]
            valve_serial = row[1]
            station_ids.append(station_id)
            station_valve_map[station_id] = valve_serial
            station_failure_map[station_id] = False
        
        print(f"[CYCLE_COMPLETE] Enabled stations: {station_ids}")
        print(f"[CYCLE_COMPLETE] Station-Valve mapping: {station_valve_map}")
        
        if not station_ids:
            return JsonResponse({"status": "error", "message": "No enabled stations found"}, status=400)

        has_station1 = 1 in station_ids
        has_station2 = 2 in station_ids
        
        # ========== STEP 3: PROCESS EACH STATION ==========
        def process_station(station_id, valve_serial):
            """Helper function to process a single station"""
            print(f"\n[CYCLE_COMPLETE] ===== Processing Station {station_id} =====")
            
            # 3a. Check for Failures
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT TEST_ID FROM temp_pressure_analysis 
                    WHERE VALVE_SER_NO = %s AND CYCLE_COMPLETE = 'No'
                """, [valve_serial])
                enabled_test_ids = [row[0] for row in cursor.fetchall()]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM temp_pressure_analysis 
                    WHERE VALVE_SER_NO = %s AND VALVE_STATUS = 'FAIL'
                """, [valve_serial])
                fail_count = cursor.fetchone()[0]
            
            # Check for failures OR no tests available
            has_no_tests = len(enabled_test_ids) == 0
            has_failure = fail_count > 0 or has_no_tests
            station_failure_map[station_id] = has_failure
            
            if has_no_tests:
                print(f"[CYCLE_COMPLETE] Station {station_id}: No test IDs found in temp_pressure_analysis - skipping count increment and reports")
            elif fail_count > 0:
                print(f"[CYCLE_COMPLETE] Station {station_id}: {fail_count} test(s) failed")
                # Reset STATUS to 0 in abrs_result_status for failed tests
                # with connection.cursor() as cursor:
                #     cursor.execute("""
                #         UPDATE abrs_result_status 
                #         SET STATUS = '0' 
                #         WHERE SERIAL_NO = %s
                #     """, [valve_serial])
            else:
                print(f"[CYCLE_COMPLETE] Station {station_id}: All tests passed")
            
            # 3b. Internal ABRS Push (only if no failures)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT TEST_ID FROM pressure_analysis
                    WHERE VALVE_SER_NO = %s AND CYCLE_COMPLETE = 'No'
                """, [valve_serial])
                test_rows = cursor.fetchall()

                for (test_id,) in test_rows:
                    if not has_failure:
                        # Check if test was actually performed (has timer data)
                        table_name = f"current_status_station{station_id}"
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {table_name}
                            WHERE VALVE_SERIAL_NO = %s AND TEST_ID = %s AND TIMER_STATUS = 1
                        """, [valve_serial, test_id])
                        timer_count = cursor.fetchone()[0]
                        
                        if timer_count > 0:
                            internal_abrs_push(valve_serial, test_id)
                            print(f"[CYCLE_COMPLETE] Station {station_id} Test {test_id}: Pushed to internal ABRS")
                        else:
                            print(f"[CYCLE_COMPLETE] Station {station_id} Test {test_id}: Skipped (not performed)")
                    else:
                        print(f"[CYCLE_COMPLETE] Station {station_id} Test {test_id}: Skipped (failure detected)")

                # Update STATUS to 0 for all tests
                cursor.execute("""
                    UPDATE temp_pressure_analysis
                    SET STATUS = 0
                    WHERE VALVE_SER_NO = %s AND CYCLE_COMPLETE = 'No'
                """, [valve_serial])

            # 3c. Reset HMI Registers
            if station_id == 1:
                hmi_addresses = [
                    (HmiAddress.S1_VALVE_SIZE, 0), (HmiAddress.S1_VALVE_CLASS, 0),
                    (HmiAddress.S1_SET_PRESSURE, 0), (HmiAddress.S1_SET_TEST_TIME, 0),
                    (HmiAddress.PRESSURE_UNIT, 0), (HmiAddress.S1_SET_CLAMPING_PRESSURE, 0),
                    (HmiAddress.S1_SET_OPEN_DEGREE, 0), (HmiAddress.S1_SET_CLOSE_DEGREE, 0),
                    (HmiAddress.S1_SET_OPEN_TORQUE, 0), (HmiAddress.S1_SET_CLOSE_TORQUE, 0),
                    (HmiAddress.S1_E_D_STATUS, 0), (HmiAddress.S1_TEST_TYPE, 0),
                    (HmiAddress.S1_HIM_TEST_TYPE, 0),
                    (HmiAddress.S1_HYDRO_SHELL_E_D_STATUS, 0), (HmiAddress.S1_HYDRO_SEAT_P_E_D_STATUS, 0),
                    (HmiAddress.S1_HYDRO_SEAT_N_E_D_STATUS, 0), (HmiAddress.S1_AIR_SEAT_P_E_D_STATUS, 0),
                    (HmiAddress.S1_AIR_SEAT_N_E_D_STATUS, 0),
                    (HmiAddress.S1_HYDRO_SHELL_TEST_STATUS, 0), (HmiAddress.S1_HYDRO_SEAT_P_TEST_STATUS, 0),
                    (HmiAddress.S1_HYDRO_SEAT_N_TEST_STATUS, 0), (HmiAddress.S1_AIR_SEAT_P_TEST_STATUS, 0),
                    (HmiAddress.S1_AIR_SEAT_N_TEST_STATUS, 0)
                ]
                for addr, val in hmi_addresses:
                    write_to_hmi(addr, val)
                
                stop_sync_both_stations()
                stop_sync_station1()
                disable_sync_station1()
            else:  # station_id == 2
                hmi_addresses = [
                    (HmiAddress.S2_VALVE_SIZE, 0), (HmiAddress.S2_VALVE_CLASS, 0),
                    (HmiAddress.S2_SET_PRESSURE, 0), (HmiAddress.S2_SET_TEST_TIME, 0),
                    (HmiAddress.PRESSURE_UNIT, 0), (HmiAddress.S2_SET_CLAMPING_PRESSURE, 0),
                    (HmiAddress.S2_SET_OPEN_DEGREE, 0), (HmiAddress.S2_SET_CLOSE_DEGREE, 0),
                    (HmiAddress.S2_SET_OPEN_TORQUE, 0), (HmiAddress.S2_SET_CLOSE_TORQUE, 0),
                    (HmiAddress.S2_E_D_STATUS, 0), (HmiAddress.S2_TEST_TYPE, 0),
                    (HmiAddress.S2_HIM_TEST_TYPE, 0),
                    (HmiAddress.S2_HYDRO_SHELL_E_D_STATUS, 0), (HmiAddress.S2_HYDRO_SEAT_P_E_D_STATUS, 0),
                    (HmiAddress.S2_HYDRO_SEAT_N_E_D_STATUS, 0), (HmiAddress.S2_AIR_SEAT_P_E_D_STATUS, 0),
                    (HmiAddress.S2_AIR_SEAT_N_E_D_STATUS, 0),
                    (HmiAddress.S2_HYDRO_SHELL_TEST_STATUS, 0), (HmiAddress.S2_HYDRO_SEAT_P_TEST_STATUS, 0),
                    (HmiAddress.S2_HYDRO_SEAT_N_TEST_STATUS, 0), (HmiAddress.S2_AIR_SEAT_P_TEST_STATUS, 0),
                    (HmiAddress.S2_AIR_SEAT_N_TEST_STATUS, 0)
                ]
                for addr, val in hmi_addresses:
                    write_to_hmi(addr, val)
                
                stop_sync_both_stations()
                stop_sync_station2()
                disable_sync_station2()

            # 3d. Save Data & Generate Reports (only if no failures)
            # IMPORTANT: save_valve_serial_no increments Count_No in serial_tbl
            # This should ONLY be called when all tests pass (no failures)
            # If any test fails, we skip incrementing the count
            if not has_failure:
                # Increment count in serial_tbl (Count_No++)
                save_valve_serial_no(valve_serial)
                print(f"[CYCLE_COMPLETE] Station {station_id}: Count incremented in serial_tbl")
                
                # Generate reports
                print(f"[CYCLE_COMPLETE] Station {station_id}: Generating reports...")
                excel_success = export_station_data(valve_serial, station_id)
                if excel_success:
                    excel_report(valve_serial, station_id)
                    merged_report(valve_serial, station_id)
                    print(f"[CYCLE_COMPLETE] Station {station_id}: Reports generated successfully")
            else:
                print(f"[CYCLE_COMPLETE] Station {station_id}: Skipping count increment and reports due to test failure(s)")

            # 3e. Clear Temp Data (always clear, regardless of pass/fail)
            cycle_complete_status(valve_serial)
            clear_temp_pressure_analysis(valve_serial)
            
            if station_id == 1:
                clear_testing_dataS1(valve_serial)
                clear_station_1()
            else:
                clear_testing_dataS2(valve_serial)
                clear_station_2()
            
            print(f"[CYCLE_COMPLETE] Station {station_id}: Processing complete")

        # Process each enabled station
        if has_station1:
            process_station(1, station_valve_map[1])
        
        if has_station2:
            process_station(2, station_valve_map[2])

        # ========== STEP 4: EXTERNAL ABRS PUSH ==========
        internal_success = True
        external_success = True
        abrs_messages = []
        
        for station_id in station_ids:
            valve_serial = station_valve_map.get(station_id)
            has_failure = station_failure_map.get(station_id, False)
            
            if valve_serial and not has_failure:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT ASSEMBLY_NO FROM abrs_result_status
                        WHERE SERIAL_NO = %s
                    """, [valve_serial])
                    row = cursor.fetchone()

                if row and row[0]:
                    external_response = external_abrs_push(valve_serial, row[0])
                    print(f"[CYCLE_COMPLETE] Station {station_id} External ABRS: {external_response}")
                    
                    if not external_response.get("success", False):
                        external_success = False
                        abrs_messages.append(f"Station {station_id}: {external_response.get('message', 'External ABRS push failed')}")
                    else:
                        abrs_messages.append(f"Station {station_id}: {external_response.get('message', 'Pushed successfully')}")
                else:
                    external_success = False
                    msg = "No assembly number found" if not row else "Assembly number is empty"
                    abrs_messages.append(f"Station {station_id}: {msg}")
                    print(f"[CYCLE_COMPLETE] Station {station_id}: {msg}")
            elif has_failure:
                abrs_messages.append(f"Station {station_id}: Skipped ABRS push due to test failure")
                print(f"[CYCLE_COMPLETE] Station {station_id}: Skipped external ABRS push (test failure)")

        # ========== STEP 5: PREPARE RESPONSE ==========
        if has_station1 and has_station2:
            base_message = "Both stations cycle completed"
        elif has_station1:
            base_message = "Station 1 cycle completed"
        elif has_station2:
            base_message = "Station 2 cycle completed"
        else:
            base_message = "Cycle completed"
        
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
        print(f"[CYCLE_COMPLETE ERROR] {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "success": False, "message": str(e)}, status=500)









# def cycle_complete(request, stationNum, valveSerial):

#     if request.method != "POST":
#         return JsonResponse({"error": "Invalid method"}, status=405)
    
#     try:        
#         stationNum = int(stationNum)
#         # Check pressure drain and cycle test status before allowing cycle complete
#         pressure_drain_status = getstatus(HmiAddress.S1_PRESSURE_DRAIN) 
#         cycle_start_stop_status = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS) 
        
#         print(f"[CYCLE_COMPLETE] Pressure Drain Status: {pressure_drain_status}, Cycle Test Status: {cycle_start_stop_status}")
        
#         # Only allow cycle complete if both are 0
#         if pressure_drain_status != 0 or cycle_start_stop_status != 0:
#             return JsonResponse({
#                 "success": False,
#                 "message": "Cannot complete cycle. Pressure drain or cycle test is still in progress."
#             }, status=400)
        
#         # Get the test IDs that are actually enabled for this valve
#         with connection.cursor() as cursor:
#             cursor.execute("SELECT TEST_ID FROM temp_pressure_analysis WHERE VALVE_SER_NO = %s AND CYCLE_COMPLETE = 'No'", [valveSerial])
#             test_rows = cursor.fetchall()            
#             enabled_test_ids = [row[0] for row in test_rows]
        
#         # Check test status from temp_pressure_analysis table (VALVE_STATUS column)
#         # If any test has VALVE_STATUS = 'FAIL', skip reports and reset COUNT_ID to 0
#         # If VALVE_STATUS is 'PASS' or empty/null (not performed), generate reports
#         skip_reports = False
#         has_failed_test = False
#         tests_without_timer = []  # Track which tests have no timer data
        
#         with connection.cursor() as cursor:
#             for test_id in enabled_test_ids:
#                 # Get VALVE_STATUS from temp_pressure_analysis
#                 cursor.execute("""
#                     SELECT VALVE_STATUS 
#                     FROM temp_pressure_analysis 
#                     WHERE VALVE_SER_NO = %s AND TEST_ID = %s AND CYCLE_COMPLETE = 'No'
#                 """, [valveSerial, test_id])
#                 result = cursor.fetchone()
#                 valve_status = result[0] if result and result[0] else None
                
#                 print(f"[CYCLE_COMPLETE] Test ID {test_id}: VALVE_STATUS = {valve_status}")
                
#                 # If any test has VALVE_STATUS = 'FAIL', skip reports and mark for COUNT_ID reset
#                 if valve_status == 'FAIL':
#                     skip_reports = True
#                     has_failed_test = True
#                     print(f"[CYCLE_COMPLETE] Test ID {test_id} failed (VALVE_STATUS = FAIL), will reset COUNT_ID to 0")
#                     break
                
#                 # Check if this test has timer data (was actually performed)
#                 cursor.execute("""
#                     SELECT COUNT(*) 
#                     FROM current_status_station1 
#                     WHERE VALVE_SERIAL_NO = %s AND TEST_ID = %s AND TIMER_STATUS = 1
#                 """, [valveSerial, test_id])
#                 timer_count = cursor.fetchone()[0]
#                 if timer_count == 0:
#                     tests_without_timer.append(test_id)
#                     print(f"[CYCLE_COMPLETE] Test ID {test_id} has no timer data (not performed)")
        
#         # If any test failed, set COUNT_ID to NULL (empty) to mark as failed
#         if has_failed_test:
#             with connection.cursor() as cursor:
#                 # First, get the current COUNT_ID from temp_pressure_analysis
#                 cursor.execute("""
#                     SELECT DISTINCT COUNT_ID 
#                     FROM temp_pressure_analysis     
#                     WHERE VALVE_SER_NO = %s AND CYCLE_COMPLETE = 'No'
#                 """, [valveSerial])
#                 count_result = cursor.fetchone()
#                 current_count_id = count_result[0] if count_result else None
                
#                 if current_count_id is not None:
#                     # Update temp_pressure_analysis - set COUNT_ID to NULL
#                     cursor.execute("""
#                         UPDATE temp_pressure_analysis 
#                         SET COUNT_ID = NULL 
#                         WHERE VALVE_SER_NO = %s AND COUNT_ID = %s AND CYCLE_COMPLETE = 'No'
#                     """, [valveSerial, current_count_id])
#                     temp_rows_updated = cursor.rowcount
                    
#                     # Update pressure_analysis - set COUNT_ID to NULL
#                     cursor.execute("""
#                         UPDATE pressure_analysis 
#                         SET COUNT_ID = NULL 
#                         WHERE VALVE_SER_NO = %s AND COUNT_ID = %s
#                     """, [valveSerial, current_count_id])
#                     pressure_rows_updated = cursor.rowcount
                    
#                     print(f"[CYCLE_COMPLETE] Set COUNT_ID to NULL (from {current_count_id}) for {valveSerial} due to failed test(s)")
#                     print(f"[CYCLE_COMPLETE] Updated {temp_rows_updated} rows in temp_pressure_analysis, {pressure_rows_updated} rows in pressure_analysis")
#                 else:
#                     print(f"[CYCLE_COMPLETE] Could not find COUNT_ID for {valveSerial}, skipping COUNT_ID reset")
        
#         # If all enabled tests have no timer data, it means tests were clicked but not performed
#         all_tests_not_performed = len(tests_without_timer) == len(enabled_test_ids) and len(enabled_test_ids) > 0
        
#         if not skip_reports:
#             # STEP 1: Push to ABRS FIRST (populates abrs_result_status with pressure/duration)
#             with connection.cursor() as cursor:
#                 #Fetch ALL pending tests BEFORE marking cycle complete
#                 cursor.execute("""
#                     SELECT TEST_ID
#                     FROM pressure_analysis
#                     WHERE VALVE_SER_NO = %s
#                     AND CYCLE_COMPLETE = 'No'
#                 """, [valveSerial])

#                 test_rows = cursor.fetchall()

#                 #Push each test to ABRS if it was performed (has timer data) and NOT failed
#                 for (test_id,) in test_rows:
#                     # Check if this test was performed (has timer on/off data)
#                     cursor.execute("""
#                         SELECT COUNT(*) 
#                         FROM current_status_station1 
#                         WHERE VALVE_SERIAL_NO = %s AND TEST_ID = %s AND TIMER_STATUS = 1
#                     """, [valveSerial, test_id])
#                     timer_count = cursor.fetchone()[0]
                    
#                     # Check if this test passed (VALVE_STATUS from temp_pressure_analysis)
#                     cursor.execute("""
#                         SELECT VALVE_STATUS 
#                         FROM temp_pressure_analysis 
#                         WHERE VALVE_SER_NO = %s AND TEST_ID = %s AND CYCLE_COMPLETE = 'No'
#                     """, [valveSerial, test_id])
#                     result = cursor.fetchone()
#                     valve_status = result[0] if result and result[0] else None
                    
#                     # Push if test was performed AND NOT failed
#                     # Push when: VALVE_STATUS = 'PASS' OR VALVE_STATUS is NULL/empty (test performed but status not set)
#                     # Don't push when: VALVE_STATUS = 'FAIL' OR test not performed (no timer data)
#                     if timer_count > 0 and valve_status != 'FAIL':
#                         # Test was performed and not failed, push to ABRS
#                         abrs_push(valveSerial, test_id)
#                         print(f"[CYCLE_COMPLETE] Pushed test ID {test_id} to ABRS (test performed, VALVE_STATUS = {valve_status})")
#                     else:
#                         if timer_count == 0:
#                             print(f"[CYCLE_COMPLETE] Skipped pushing test ID {test_id} to ABRS (test not performed)")
#                         elif valve_status == 'FAIL':
#                             print(f"[CYCLE_COMPLETE] Skipped pushing test ID {test_id} to ABRS (VALVE_STATUS = FAIL)")
            
#             # Export report - check configuration_table for enabled reports
#             with connection.cursor() as cursor:
#                 cursor.execute("SELECT GRAPH_PDF_REPORT, VTR_PDF_REPORT, VTR_CSV_REPORT FROM configuration_table WHERE ID=1")
#                 report_generation = cursor.fetchone()
#                 print('report_generation',report_generation)
                
#                 if report_generation:
#                     graph_report = report_generation[0]  # GRAPH_PDF_REPORT (merged PDF with graphs)
#                     excel_report = report_generation[1]  # VTR_PDF_REPORT (Excel template)
#                     csv_report = report_generation[2]    # VTR_CSV_REPORT (CSV export)
                    
#                     print(f"[CYCLE_COMPLETE] Report generation settings - Graph: {graph_report}, Excel: {excel_report}, CSV: {csv_report}")

#                     # IMPORTANT: Generate CSV/Excel FIRST, then PDF (PDF needs Excel file to exist)
                    
#                     # Step 1: Export CSV data to Excel file (creates the Excel file in D:/Bray_DB_export)
#                     if csv_report == "Enabled":
#                         export_station_data_to_e_drive(valveSerial, stationNum)
#                         print(f"[CYCLE_COMPLETE] CSV/Excel data exported for {valveSerial}")
                    
#                     # Step 2: Copy Excel template (needs to happen after data export)
#                     if excel_report == "Enabled":
#                         copy_excel_template_to_report_path(valveSerial, stationNum)
#                         print(f"[CYCLE_COMPLETE] Excel template report exported for {valveSerial}")
                    
#                     # Step 3: Generate Graph PDF (needs Excel file from Step 1 to exist)
#                     if graph_report == "Enabled":
#                         export_merged_report_to_e_drive(valveSerial, stationNum)
#                         print(f"[CYCLE_COMPLETE] Graph PDF report exported for {valveSerial}")
#                 else:
#                     print(f"[CYCLE_COMPLETE] No report configuration found, skipping report generation")


#             # ---------- STEP 3: EXTERNAL ABRS PUSH ----------
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     SELECT ASSEMBLY_NO
#                     FROM abrs_result_status
#                     WHERE SERIAL_NO = %s
#                 """, [valveSerial])

#                 row = cursor.fetchone()

#                 # If no record found or no assembly ID, still allow cycle complete
#                 if not row:
#                     print(f"[CYCLE_COMPLETE] No record found in abrs_result_status for {valveSerial}")
#                     # Continue to cleanup instead of returning early
#                     abrs_response = {
#                         "success": True, 
#                         "local": True,
#                         "abrs": False,
#                         "message": "Cycle completed. Data saved locally (No ABRS record found)"
#                     }
#                 elif not row[0]:
#                     print(f"[CYCLE_COMPLETE] Assembly ID missing for {valveSerial}")
#                     # Continue to cleanup instead of returning early
#                     abrs_response = {
#                         "success": True, 
#                         "local": True,
#                         "abrs": False,
#                         "message": "Cycle completed. Data saved locally (Assembly ID missing - cannot push to ABRS)"
#                     }
#                 else:
#                     abrs_response = bray_abrs_push(valveSerial, row[0])
                    
#                     # Only increment count if tests were actually enabled/selected
#                     if enabled_test_ids and len(enabled_test_ids) > 0:
#                         with connection.cursor() as cursor:
#                             cursor.execute("select Serial_No from serial_tbl where Serial_No = %s", [valveSerial])
#                             row = cursor.fetchone()
#                             if row:
#                                 cursor.execute("update serial_tbl set Count_No = Count_No + 1 where Serial_No = %s", [valveSerial])
#                             else:   
#                                 cursor.execute("insert into serial_tbl (Serial_No, Count_No) values (%s, %s)", [valveSerial, 1])
#                         print(f"[CYCLE_COMPLETE] Count incremented for {valveSerial}")
#                     else:
#                         print(f"[CYCLE_COMPLETE] No tests enabled, skipping count increment for {valveSerial}")
#         else:
#             print("[CYCLE_COMPLETE] Skipping report generation and ABRS push due to test failure(s)")
            
#             # Reset STATUS to 0 in abrs_result_status when tests fail
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     UPDATE abrs_result_status 
#                     SET STATUS = '0' 
#                     WHERE SERIAL_NO = %s
#                 """, [valveSerial])
#                 print(f"[CYCLE_COMPLETE] STATUS reset to 0 for {valveSerial} due to test failure")
            
#             abrs_response = {
#                 "success": True,
#                 "local": True,
#                 "abrs": False,
#                 "message": "Cycle completed. Tests failed - reports and ABRS push skipped."
#             }
            
#             # Increment count ONLY when ALL tests have no timer data (tests clicked but not performed)
#             if all_tests_not_performed:
#                 with connection.cursor() as cursor:
#                     cursor.execute("select Serial_No from serial_tbl where Serial_No = %s", [valveSerial])
#                     row = cursor.fetchone()
#                     if row:
#                         cursor.execute("update serial_tbl set Count_No = Count_No + 1 where Serial_No = %s", [valveSerial])
#                     else:   
#                         cursor.execute("insert into serial_tbl (Serial_No, Count_No) values (%s, %s)", [valveSerial, 1])
#                 print(f"[CYCLE_COMPLETE] Count incremented for {valveSerial} (tests clicked but not performed)")
#             else:
#                 print(f"[CYCLE_COMPLETE] Tests failed after running, skipping count increment for {valveSerial}")
#                 print(f"[CYCLE_COMPLETE] Count incremented for {valveSerial} (tests failed)")
#             # else:
#             #     print(f"[CYCLE_COMPLETE] No tests enabled, skipping count increment for {valveSerial}")
        
        

#         # Copy Excel template from bray_app to report path AFTER ABRS push
#         # This ensures abrs_result_status has the latest data
#         # Only generate Excel template if tests passed
#         # if not skip_reports:
#         #     copy_excel_template_to_report_path(valveSerial, stationNum)
#         # else:
#         #     print("[CYCLE_COMPLETE] Skipping Excel template generation due to test failure")
        
#         with connection.cursor() as cursor:
#             # Update STATUS to 0 for all tests when cycle completes
#             cursor.execute("""
#                 UPDATE temp_pressure_analysis
#                 SET STATUS = 0
#                 WHERE VALVE_SER_NO = %s
#                 AND CYCLE_COMPLETE = 'No'
#             """, [valveSerial])

#             #Now mark cycle complete
#             cursor.execute("""
#                 UPDATE pressure_analysis
#                 SET CYCLE_COMPLETE = 'Yes',CYCLE_COMPLETED_DATE= NOW()
#                 WHERE VALVE_SER_NO = %s
#             """, [valveSerial])
            

#             #Station specific cleanup
#             if stationNum == 1:
#                 cursor.execute("""
#                     UPDATE master_temp_data
#                     SET STATION_STATUS = 'Disabled'
#                     WHERE ID = 1
#                 """)

#                 # cursor.execute("""
#                 #     DELETE FROM temp_testing_data_s1
#                 #     WHERE VALVE_SERIAL_NO = %s
#                 # """, [valveSerial])

#                 # cursor.execute("""
#                 #     DELETE FROM temp_pressure_analysis
#                 #     WHERE VALVE_SER_NO = %s
#                 # """, [valveSerial])
                
#                 cursor.execute("""
#                     TRUNCATE TABLE temp_testing_data_s1
#                     """)

#                 cursor.execute("""
#                     TRUNCATE TABLE temp_pressure_analysis
#                     """)


#                 # Set all S1 HMI addresses to 0 (addresses 2000-2036)
#                 # for address in range(2000, 2045):
#                 #     write_to_hmi(address, 0)

#                 write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
#                 write_to_hmi(HmiAddress.S1_VALVE_SIZE, 0)
#                 write_to_hmi(HmiAddress.S1_VALVE_CLASS, 0)
#                 write_to_hmi(HmiAddress.S1_SET_PRESSURE, 0)
#                 write_to_hmi(HmiAddress.S1_SET_HOLDING_TIME, 0)
#                 write_to_hmi(HmiAddress.S1_SET_OPEN_DEGREE, 0)
#                 write_to_hmi(HmiAddress.S1_SET_CLOSE_DEGREE, 0)
#                 write_to_hmi(HmiAddress.PRESSURE_UNIT, 0)
#                 write_to_hmi(HmiAddress.S1_SET_TEST_TIME, 0)
#                 write_to_hmi(HmiAddress.S1_TEST_RESULT, 0)
#                 write_to_hmi(HmiAddress.S1_E_D_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_HYDRO_SHELL_E_D_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_HYDRO_SEAT_P_E_D_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_HYDRO_SEAT_N_E_D_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_AIR_SEAT_P_E_D_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_AIR_SEAT_N_E_D_STATUS, 0)

#                 write_to_hmi(HmiAddress.S1_HYDRO_SHELL_TEST_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_HYDRO_SEAT_P_TEST_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_HYDRO_SEAT_N_TEST_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_AIR_SEAT_P_TEST_STATUS, 0)
#                 write_to_hmi(HmiAddress.S1_AIR_SEAT_N_TEST_STATUS, 0)
                
#                 stop_station1()
#                 clear_station_1()

#             else:
#                 return JsonResponse({"error": "Invalid station number"},status=400)
        
#         # Return the response after all cleanup is done
#         return JsonResponse(abrs_response)

#     except Exception as e:
#         return JsonResponse({"status": "error", "success": False, "message": str(e)}, status=500)
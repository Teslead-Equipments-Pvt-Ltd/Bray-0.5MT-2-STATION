from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from bray_app.services.save_station1_service import (
    save_station1, save_station2, insert_pressure_duration, insert_pressure_duration_s2,
    check_duplicate_serial_station1, check_duplicate_serial_station2, check_hmi_connection
)
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx
from bray_app.src import HmiAddress
from django.db import connection


def write_to_hmi(place, value):
    try:
        TestleadSmartsyncx.write_register(place, value)
        return True
    except Exception as e:
        print(f"[Error writing to HMI] {e}")
        isconnected = False
        return False

@csrf_exempt
def save_station1_form(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        # Check HMI connection status before saving
        if not check_hmi_connection():
            return JsonResponse({
                "status": "error",
                "message": "HMI is not connected. Please connect HMI before saving the form."
            }, status=400)
        
        data = json.loads(request.body.decode("utf-8"))
    
        fields = data.get("fields", [])
        field_dict = {item.get("name"): item.get("value") for item in fields}
        pressureunit = field_dict.get("pressureunit_s1")
        
        # Check if both stations have the same serial number
        station1_serial = field_dict.get("VALVE_SER_NO")
        is_duplicate, station2_serial = check_duplicate_serial_station1(station1_serial)
        
        if is_duplicate:
            return JsonResponse({
                "status": "error",
                "message": f"Duplicate serial number detected! Serial number '{station1_serial}' is already used in Station 2. Please use a different serial number."
            }, status=400)
        
        station_status = "Enabled"
        cycle_complete = "No"
        testname = data.get("testname")
        test_pressure = data.get("test_pressure")
        test_duration = data.get("test_duration")
        active_testid = data.get("test_id")
        diabled_testid = data.get("diabled_testid")
        open_degree_s1 = data.get("open_degree_s1")
        close_degree_s1 = data.get("close_degree_s1")
        testmode = data.get("test_mode")
        
        print(f"[DEBUG] Received degree values - Open: {open_degree_s1}, Close: {close_degree_s1}")
        
        # Validate degree values
        if open_degree_s1 is None or close_degree_s1 is None:
            return JsonResponse({
                "status": "error",
                "message": "Set open degree and close degree values are required but not received."
            }, status=400)
        
        # Check if at least one test is active (enabled)
        if not active_testid or len(active_testid) == 0:
            return JsonResponse({
                "status": "error",
                "message": "Please enable at least one test to proceed. Cannot save form without any active tests."
            }, status=400)
        
        # Check if all tests are disabled
        if diabled_testid and len(diabled_testid) >= len(active_testid):
            return JsonResponse({
                "status": "error",
                "message": "Please enable at least one test to proceed. All tests are currently disabled."
            }, status=400)
        if testmode == 1:
            test_mode = "Sync"
        else:
            test_mode = "Non_Sync"
        
        
        # Write to Modbus registers
        try:
            print("printing")
            print('open degree',open_degree_s1)
            # Convert to int and handle potential conversion errors
            try:
                open_deg_int = int(float(open_degree_s1)) if open_degree_s1 is not None else 0
                close_deg_int = int(float(close_degree_s1)) if close_degree_s1 is not None else 0
            except (ValueError, TypeError) as e:
                print(f"Error converting degree values to int: {e}")
                return JsonResponse({
                    "status": "error",
                    "message": f"Invalid degree values. Open: {open_degree_s1}, Close: {close_degree_s1}"
                }, status=400)
                
            write_to_hmi(HmiAddress.S1_SET_OPEN_DEGREE, open_deg_int)
            write_to_hmi(HmiAddress.S1_SET_CLOSE_DEGREE, close_deg_int)
            print("inserted")
        

        except Exception as e:
            print(f"Error writing to Modbus: {e}")
          
        
        if not fields:
            return JsonResponse({"error": "No fields found"}, status=400)

        # Convert list → dictionary
        field_dict = {item["name"]: item["value"] for item in fields}

        # Prepare dynamic fields for COLx_NAME and COLx_VALUE
        update_fields = []
        update_values = []

        index = 1
        for key, value in field_dict.items():
            # Skip system fields
            if key in ["size_s1", "class_s1", "pressureunit_s1",
                       "standard_s1", "type_s1", "body_material_s1","" "VALVE_SER_NO"]:
                continue

            if index > 23:
                break  # limit to COL1–COL23

            update_fields.append(f"COL{index}_NAME = %s")
            update_fields.append(f"COL{index}_VALUE = %s")
            update_values.append(key)     # name
            update_values.append(value)   # value
            index += 1

        # Add final fixed fields
        update_fields += [
            "SIZE_NAME = %s",
            "CLASS_NAME = %s",
            "PRESSURE_UNIT = %s",
            "STANDARD_NAME = %s",
            "TYPE_NAME = %s",
            "SHELL_MATERIAL_NAME = %s",
            "SYNC_NON_SYNC_STATUS = %s",
            "VALVE_SER_NO = %s",
            "STATION_STATUS = %s",
            "CYCLE_COMPLETE = %s"
        ]

        update_values += [
            field_dict.get("size_s1"),
            field_dict.get("class_s1"),
            field_dict.get("pressureunit_s1"),
            field_dict.get("standard_s1"),
            field_dict.get("type_s1"),
            field_dict.get("body_material_s1"),
            test_mode,
            field_dict.get("VALVE_SER_NO"),
            station_status,
            cycle_complete
        ]

        # Add WHERE ID
        update_values.append(1)

        # Build final update query
        query = f"""
            UPDATE master_temp_data
            SET {', '.join(update_fields)}
            WHERE ID = %s
        """

        save_station1(query,update_values)
        
        valve_serial_no = field_dict.get("VALVE_SER_NO")
        insert_pressure_duration(testname,test_pressure,test_duration,active_testid,diabled_testid,pressureunit,valve_serial_no)

        return JsonResponse({"status": "success", "message": "Updated master_temp_data successfully"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
    
    
    
@csrf_exempt
def save_station2_form(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        # Check HMI connection status before saving
        if not check_hmi_connection():
            return JsonResponse({
                "status": "error",
                "message": "HMI is not connected. Please connect HMI before saving the form."
            }, status=400)
        
        data = json.loads(request.body.decode("utf-8"))

        fields = data.get("fields", [])
        field_dict = {item.get("name"): item.get("value") for item in fields}
        pressureunit = field_dict.get("pressureunit_s2")
        
        # Check if both stations have the same serial number
        station2_serial = field_dict.get("VALVE_SER_NO_s2")
        is_duplicate, station1_serial = check_duplicate_serial_station2(station2_serial)
        
        if is_duplicate:
            return JsonResponse({
                "status": "error",
                "message": f"Duplicate serial number detected! Serial number '{station2_serial}' is already used in Station 1. Please use a different serial number."
            }, status=400)
        
        station_status = "Enabled"
        cycle_complete = "No"
        testname = data.get("testname")
        test_pressure = data.get("test_pressure")
        test_duration = data.get("test_duration")
        active_testid = data.get("test_id")
        diabled_testid = data.get("diabled_testid")
        open_degree_s2 = data.get("open_degree_s2")
        close_degree_s2 = data.get("close_degree_s2")
        testmode = data.get("test_mode")
        
        print(f"[DEBUG] Station 2 - Received degree values - Open: {open_degree_s2}, Close: {close_degree_s2}")
        
        # Validate degree values
        if open_degree_s2 is None or close_degree_s2 is None:
            return JsonResponse({
                "status": "error",
                "message": "Set open degree and close degree values are required but not received."
            }, status=400)
        # print(""testmode)
        
        # Check if at least one test is active (enabled)
        if not active_testid or len(active_testid) == 0:
            return JsonResponse({
                "status": "error",
                "message": "Please enable at least one test to proceed. Cannot save form without any active tests."
            }, status=400)
        
        # Check if all tests are disabled
        if diabled_testid and len(diabled_testid) >= len(active_testid):
            return JsonResponse({
                "status": "error",
                "message": "Please enable at least one test to proceed. All tests are currently disabled."
            }, status=400)
        if testmode == 1:
            test_mode = "Sync"
        else:
            test_mode = "Non_Sync"
        
        # Write to Modbus registers
        try:
            # Convert to int and handle potential conversion errors
            try:
                open_deg_int = int(float(open_degree_s2)) if open_degree_s2 is not None else 0
                close_deg_int = int(float(close_degree_s2)) if close_degree_s2 is not None else 0
            except (ValueError, TypeError) as e:
                print(f"Error converting degree values to int: {e}")
                return JsonResponse({
                    "status": "error",
                    "message": f"Invalid degree values. Open: {open_degree_s2}, Close: {close_degree_s2}"
                }, status=400)
                
            write_to_hmi(HmiAddress.S2_SET_OPEN_DEGREE, open_deg_int)
            write_to_hmi(HmiAddress.S2_SET_CLOSE_DEGREE, close_deg_int)

        except Exception as e:
            print(f"Error writing to Modbus: {e}")
        
        if not fields:
            return JsonResponse({"error": "No fields found"}, status=400)

        # Convert list → dictionary
        field_dict = {item["name"]: item["value"] for item in fields}

        # Prepare dynamic fields for COLx_NAME and COLx_VALUE
        update_fields = []
        update_values = []

        index = 1
        for key, value in field_dict.items():
            # Skip system fields
            if key in ["size_s2", "class_s2", "pressureunit_s2",
                       "standard_s2", "type_s2", "body_material_s2", "VALVE_SER_NO_s2"]:
                continue

            if index > 23:
                break  # limit to COL1–COL23

            update_fields.append(f"COL{index}_NAME = %s")
            update_fields.append(f"COL{index}_VALUE = %s")
            update_values.append(key)     # name
            update_values.append(value)   # value
            index += 1

        # Add final fixed fields
        update_fields += [
            "SIZE_NAME = %s",
            "CLASS_NAME = %s",
            "PRESSURE_UNIT = %s",
            "STANDARD_NAME = %s",
            "TYPE_NAME = %s",
            "SHELL_MATERIAL_NAME = %s",
            "SYNC_NON_SYNC_STATUS = %s",
            "VALVE_SER_NO = %s",
            "STATION_STATUS = %s",
            "CYCLE_COMPLETE = %s"
        ]

        update_values += [
            field_dict.get("size_s2"),
            field_dict.get("class_s2"),
            field_dict.get("pressureunit_s2"),
            field_dict.get("standard_s2"),
            field_dict.get("type_s2"),
            field_dict.get("body_material_s2"),
            test_mode,
            field_dict.get("VALVE_SER_NO_s2"),
            station_status,
            cycle_complete
        ]

        # Add WHERE ID
        update_values.append(2)

        # Build final update query
        query = f"""
            UPDATE master_temp_data
            SET {', '.join(update_fields)}
            WHERE ID = %s
        """

        save_station2(query,update_values)
        
        valve_serial_no_s2 = field_dict.get("VALVE_SER_NO_s2")
        insert_pressure_duration_s2(testname,test_pressure,test_duration,active_testid,diabled_testid,pressureunit,valve_serial_no_s2)
        return JsonResponse({"status": "success", "message": "Updated master_temp_data successfully"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

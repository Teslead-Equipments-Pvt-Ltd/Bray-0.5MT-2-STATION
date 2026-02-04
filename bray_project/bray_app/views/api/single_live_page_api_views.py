import json
from pymodbus.client import ModbusTcpClient
from django.db import connection, transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime
import time
# from bray_app.decorators import permission_required
from django.views.decorators.csrf import csrf_exempt
from pymodbus.client import ModbusTcpClient
import pyodbc
import threading, os
from openpyxl import Workbook
from io import BytesIO
import struct
import asyncio
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx, ABRSDatabase
from bray_app.services.abrs_service import ABRSService

# Imports for report generation
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from django.template.loader import render_to_string
from weasyprint import HTML

from bray_app.src import HmiAddress
from bray_app.services.single_live_page_services import( 
    clear_station_1, 
    clear_station_2, 
    clear_s1_livedata,
    clear_s2_livedata,
    save_test_pressure_station1, 
    save_test_pressure_station2)


def check_abrs_hmi_connection(request):
    # ---- ABRS DB CHECK ----
    try:
        db = ABRSDatabase()
        abrs_status = db.test_connection()
        print("abrs status", abrs_status)
    except Exception as e:
        print("ABRS connection error:", e)
        abrs_status = False

    # ---- HMI CHECK ----
    try:
        hmi_value = getstatus(HmiAddress.S1_VALVE_SIZE)
        hmi_status = hmi_value is not None
        print("hmi status", hmi_status)
    except Exception as e:
        print("HMI error:", e)
        hmi_status = False

    return JsonResponse({
        "abrs_connected": abrs_status,
        "hmi_connected": hmi_status,
      
    })



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

def get_result(request):
    """Get test result from HMI - accessible globally"""
    try:
        # Read test result from HMI address 2017 for Station 1
        S1_test_result = getstatus(HmiAddress.S1_TEST_RESULT)
        S2_test_result = getstatus(HmiAddress.S2_TEST_RESULT)
        
        S1_result_text = "UNKNOWN"
        S2_result_text = "UNKNOWN"
        
        if S1_test_result is not None:
            # Convert HMI result to PASS/FAIL
            S1_result_text = "PASS" if S1_test_result == 1 else "FAIL"
        
        if S2_test_result is not None:
            # Convert HMI result to PASS/FAIL
            S2_result_text = "PASS" if S2_test_result == 1 else "FAIL"
            
        return JsonResponse({
            "status": "success",
            "S1_test_result": S1_test_result,
            "S1_result_text": S1_result_text,
            "S2_test_result": S2_test_result,
            "S2_result_text": S2_result_text,
            "hmi_address": HmiAddress.S1_TEST_RESULT
        })
            
    except Exception as e:
        print(f"Error reading HMI test result: {e}")
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "S1_test_result": None,
            "S1_result_text": "UNKNOWN",
            "S2_test_result": None,
            "S2_result_text": "UNKNOWN"
        })
            

def check_status(request):
    try:
        with connection.cursor() as cursor:

            cursor.execute("SELECT STATION_STATUS FROM master_temp_data WHERE id=1")
            station1_status = cursor.fetchone()[0].lower()
          
            cursor.execute("SELECT STATION_STATUS FROM master_temp_data WHERE id=2")
            station2_status = cursor.fetchone()[0].lower()

            s1_test_mode = getstatus(HmiAddress.S1_MACHINE_MODE)

            s2_test_mode = getstatus(HmiAddress.S2_MACHINE_MODE)
          

        # Final consistent return
        return JsonResponse({
            "status": "success",
            "station1_status": station1_status,
            "station2_status": station2_status,
            "s1_test_mode": s1_test_mode,
            "s2_test_mode": s2_test_mode
        })

    except Exception as e:
        print("Error in check_status:", e)
        return JsonResponse({"status": "failure"})
    
    
def enabled_test_buttons(request):

    try:
        with connection.cursor() as cursor:
            # Fetch statuses
            cursor.execute("SELECT TEST_ID, VALVE_SERIAL_NO, TEST_NAME, TESTING_PR_UNIT, TESTING_DUR_UNIT FROM temp_testing_data_s1")
            s1_enabled_buttons = cursor.fetchall()

            s1_enabled_tst_buttons = []
            for btns in s1_enabled_buttons:
                s1_enabled_tst_buttons.append({
                    "id": btns[0],
                    "valve_serial_no":btns[1],
                    "name": btns[2],
                    "psr_unit":btns[3],
                    "dur_unit":btns[4] 
                })

            # print(s1_enabled_tst_buttons)

            cursor.execute("SELECT TEST_ID, VALVE_SERIAL_NO, TEST_NAME, TESTING_PR_UNIT, TESTING_DUR_UNIT   FROM temp_testing_data_s2")
            s2_enabled_test_buttons = cursor.fetchall()
            
            s2_enabled_tst_buttons = []
            for btns in s2_enabled_test_buttons:
                s2_enabled_tst_buttons.append({
                    "id": btns[0],
                    "valve_serial_no":btns[1],
                    "name": btns[2],
                    "psr_unit":btns[3],
                    "dur_unit":btns[4] 
                })
            # print(s2_enabled_tst_buttons)

        return JsonResponse({
            "status": "success",
            "s1_enabled_tst_btns":s1_enabled_tst_buttons,
            "s2_enabled_tst_btns":s2_enabled_tst_buttons
            })
    except:
        return JsonResponse({"status": "failure"})
    


# def getStation_values(request):
#     try:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME, PRESSURE_UNIT, SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS
#                 FROM master_temp_data
#                 WHERE id = 1
#             """)
#             S1_row = cursor.fetchone()

#             #hmi read
#             s1_open_torque = getstatus(HmiAddress.S1_SET_OPEN_TORQUE)
#             s1_close_torque = getstatus(HmiAddress. S1_SET_CLOSE_TORQUE)
         
#             if S1_row:
#                 valve_ser_no, size, cls, psr_unit, body_material, assembledby, testedby, station_status = S1_row

              
#                 S1_data = {
#                     "valve_ser_no":valve_ser_no,
#                     "size": size,
#                     "class": cls,
#                     "psr_unit":psr_unit,
#                     "body": body_material,
#                     "testedby": testedby,
#                     "assembledby": assembledby,
#                     "s1_torque_value":{
#                     "open_torque": s1_open_torque,
#                     "close_torque":s1_close_torque
#                     } 
#                 }
                
#             cursor.execute("""
#             SELECT SIZE_ID, SIZE_NAME  
#             FROM valvesize
#             WHERE SIZE_NAME = %s
#             """, [size])
#             s1_v_size = cursor.fetchone()   
            
#             #hmi write
#             if s1_v_size:
#                 s1_size_id = s1_v_size[0]     
#                 write_to_hmi(HmiAddress.S1_VALVE_SIZE, s1_size_id)

#             write_to_hmi(HmiAddress.S1_VALVE_CALSS, cls)
#             write_to_hmi(HmiAddress.PRESSURE_UNIT, psr_unit)
#             if station_status == "Enabled":
#                 write_to_hmi(HmiAddress.S1_E_D_STATUS, 1)
#             else:
#                 write_to_hmi(HmiAddress.S1_E_D_STATUS, 0)
    
           
#             cursor.execute("""
#                 SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME,PRESSURE_UNIT, SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS 
#                 FROM master_temp_data
#                 WHERE id = 2
#                 """)
#             S2_row = cursor.fetchone()

#             s2_open_torque = getstatus(HmiAddress.S2_SET_OPEN_TORQUE)
#             s2_close_torque = getstatus(HmiAddress.S2_SET_CLOSE_TORQUE)

#             if S2_row:
#                 # Pythonic tuple unpacking
#                 valve_ser_no, size, cls, psr_unit, body_material, assembledby, testedby, station_status2 = S2_row

#                 S2_data = {
#                     "valve_ser_no":valve_ser_no,
#                     "size": size,
#                     "class": cls,
#                     "psr_unit":psr_unit,
#                     "body": body_material,
#                     "testedby": testedby,
#                     "assembledby": assembledby,
#                     "s2_torque_value":{
#                     "open_torque": s2_open_torque,
#                     "close_torque":s2_close_torque
#                     } 
#                 }

#                 cursor.execute("""
#                     SELECT SIZE_ID, SIZE_NAME  
#                     FROM valvesize
#                     WHERE SIZE_NAME = %s
#                     """, [size])
#                 s2_v_size = cursor.fetchone()   # get single row

#                 if s2_v_size:
#                     s2_size_id = s2_v_size[0]      # extract SIZE_ID
#                     write_to_hmi(HmiAddress.S2_VALVE_SIZE, s2_size_id)

#                 write_to_hmi(HmiAddress.S2_VALVE_CALSS, cls)
#                 write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, psr_unit)
                
#                 if station_status2 == "Enabled":
#                     write_to_hmi(HmiAddress.S2_E_D_STATUS, 1)
#                 else:
#                     write_to_hmi(HmiAddress.S2_E_D_STATUS, 0)

#                 return JsonResponse({
#                     "status": "success",
#                     "S1_data": S1_data,
#                     "S2_data": S2_data
#                 })
#             else:
#                 return JsonResponse({
#                     "status": "failure",
#                     "message": "No data found for Station 1."
#                 })

#     except Exception as e:
#         print("Error in getStation1_values:", e)
#         return JsonResponse({
#             "status": "failure",
#             "message": str(e)
#         })
    


def getStation_values(request, stationNum):
    print("get values for station", stationNum)

    if stationNum not in [1, 2]:
        return JsonResponse({"status": "error", "message": "Invalid station"})

    if stationNum == 1:
        data = getStation_values1()
        print("station 1 values", data)
        return JsonResponse({"status": "success","S1_data": data})
       
    else:
        data = getStation_values2()
        print("station2 values", data)
        return JsonResponse({"status": "success", "S2_data": data})


def getStation_values1():

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME, PRESSURE_UNIT, SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS
                FROM master_temp_data
                WHERE id = 1
            """)
            S1_row = cursor.fetchone()

            #hmi read
            s1_open_degree = getstatus(HmiAddress.S1_SET_OPEN_DEGREE)
            s1_close_degree = getstatus(HmiAddress. S1_SET_CLOSE_DEGREE)

        
            if S1_row:
                valve_ser_no, size, cls, psr_unit, body_material, assembledby, testedby, station_status = S1_row

            
                S1_data = {
                    "valve_ser_no":valve_ser_no,
                    "size": size,
                    "class": cls,
                    "psr_unit":psr_unit,
                    "body": body_material,
                    "testedby": testedby,
                    "assembledby": assembledby,
                    "s1_degree_value":{
                    "open_degree": s1_open_degree,
                    "close_degree":s1_close_degree
                    } 
                }
                
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

            write_to_hmi(HmiAddress.S1_VALVE_CLASS, cls)
            write_to_hmi(HmiAddress.PRESSURE_UNIT, psr_unit)
            write_to_hmi(HmiAddress.S1_E_D_STATUS, 1 if station_status == "Enabled" else 0)
            
            return S1_data
            
    except Exception as e:
        print("Error in getStation1_values:", e)
        return {str(e)}


def getStation_values2(): 

    try:
        with connection.cursor() as cursor:   
            cursor.execute("""
                SELECT VALVE_SER_NO, SIZE_NAME, CLASS_NAME,PRESSURE_UNIT, SHELL_MATERIAL_NAME, COL7_VALUE, COL8_VALUE, STATION_STATUS 
                FROM master_temp_data
                WHERE id = 2
                """)
            S2_row = cursor.fetchone()

            s2_open_degree = getstatus(HmiAddress.S2_SET_OPEN_DEGREE)
            s2_close_degree = getstatus(HmiAddress.S2_SET_CLOSE_DEGREE)

            if S2_row:
                # Pythonic tuple unpacking
                valve_ser_no, size, cls, psr_unit, body_material, assembledby, testedby, station_status2 = S2_row

                S2_data = {
                    "valve_ser_no":valve_ser_no,
                    "size": size,
                    "class": cls,
                    "psr_unit":psr_unit,
                    "body": body_material,
                    "testedby": testedby,
                    "assembledby": assembledby,
                    "s2_degree_value":{
                    "open_degree": s2_open_degree,
                    "close_degree":s2_close_degree
                    } 
                }

                cursor.execute("""
                    SELECT SIZE_ID, SIZE_NAME  
                    FROM valvesize
                    WHERE SIZE_NAME = %s
                    """, [size])
                s2_v_size = cursor.fetchone()   # get single row

                if s2_v_size:
                    s2_size_id = s2_v_size[0]      # extract SIZE_ID
                    write_to_hmi(HmiAddress.S2_VALVE_SIZE, s2_size_id)

                write_to_hmi(HmiAddress.S2_VALVE_CLASS, cls)
                write_to_hmi(HmiAddress.PRESSURE_UNIT, psr_unit)
                write_to_hmi(HmiAddress.S2_E_D_STATUS, 1 if station_status2 == "Enabled" else 0)

                return S2_data

    except Exception as e:
        print("Error in getStation2_values:", e)
        return{str(e)}
    
    
    

def get_test_set_pressure(request, id, valve_serial_no, name, stationNum, units):
   

    if request.method != "GET":
        return JsonResponse ({"error":"Invalid method"}, status = 405)
    
    print(id, valve_serial_no, name, stationNum, units)
     
    allowed_units = ["BAR", "PSI", "KG"]

    if units not in allowed_units:
        raise ValueError("Invalid unit type")
    
    column_name = f"TESTING_PR_{units}" 

    try:
        if (stationNum == 1):

            set_bubble_count = getstatus(HmiAddress.S1_SET_BUBBLE_COUNT)
            set_clampping_psr = getstatus(HmiAddress.S1_SET_CLAMPING_PRESSURE)
            
            with connection.cursor() as cursor:
                query = f"""
                        SELECT TEST_ID, TEST_NAME, TEST_MEDIUM,
                        TEST_CATEGORY, TESTING_PR_UNIT, {column_name}, TESTING_DUR_UNIT, TESTING_DUR_SEC
                        FROM temp_testing_data_s1
                        WHERE TEST_ID = %s AND TEST_NAME = %s
                    """
                cursor.execute(query, [id, name])
                station_1 = cursor.fetchall()

                station_data1 = {}

                for row in station_1:

                    test_id = row[0]
                    test_name = row[1]
                    pressure_unit = row[4]
                    set_pressure = row[5]
                    dur_unit = row[6]
                    set_duration = row[7]

                    station_data1= {
                    "TEST_ID": test_id ,
                    "TEST_NAME": test_name,
                    "TESTING_PSR_UNIT":pressure_unit,
                    "TESTING_PRESSURE": set_pressure,
                    "TESTING_DUR_UNIT":dur_unit,
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
                print(station1_cls)

                
                
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
                    write_to_hmi(HmiAddress.S1_VALVE_CLASS, int(s1_class))
                 
                    if  pressure_unit == 'psi':
                        write_to_hmi(HmiAddress.PRESSURE_UNIT, 1)

                    elif pressure_unit == 'bar':
                        write_to_hmi(HmiAddress.PRESSURE_UNIT, 2)

                    else:
                        pressure_unit == 'kg/cm2g'
                        write_to_hmi(HmiAddress.PRESSURE_UNIT, 3)

                    
                    write_to_hmi(HmiAddress. S1_TEST_TYPE, int(test_id))
                    start_single_station_threads(station1_enabled = True) 
                    print("station-1 thread is called for store station-1 pressure")

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

                for i in range(1, 24):
                    col_name = data.get(f"COL{i}_NAME")
                    value = data.get(f"COL{i}_VALUE")

                    if name:  # ignore empty/null columns
                        parameters[col_name] = value
                        # print("parameters", parameters)
                        

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
        
        elif stationNum == 2:

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
                # master_station_data2 = []


                for row in station_2:
                    s2_valve_serial_no = row[0]
                    s2_test_id = row[1]
                    s2_test_name = row[2]
                    s2_pressure_unit = row[5]
                    s2_set_pressure = row[6]
                    s2_dur_unit = row[7]
                    s2_set_duration = row[8]
                   
                    station2_data={
                    "VALVE_SERIAL_NO":s2_valve_serial_no,
                    "TEST_ID": s2_test_id,
                    "TEST_NAME": s2_test_name,
                    "TESTING_PSR_UNIT":s2_pressure_unit,
                    "TESTING_PRESSURE": s2_set_pressure,
                    "TESTING_DUR_UNIT":s2_dur_unit,
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
                write_to_hmi(HmiAddress.S2_SET_TEST_TIME, int( s2_set_duration))
                write_to_hmi(HmiAddress.S2_VALVE_CLASS, int(s2_class))
                
                
                if  s2_pressure_unit == 'psi':
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, 1)

                elif s2_pressure_unit == 'bar':
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, 2)

                else:
                    s2_pressure_unit == 'kg/cm2g'
                    write_to_hmi(HmiAddress.PRESSURE_UNIT, 3)

                
                write_to_hmi(HmiAddress. S2_TEST_TYPE, int(s2_test_id))
                start_single_station_threads(station2_enabled = True) 
                print("station-2 thread is called for store station-2 pressure")
        
                
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

                for i in range(1, 24):
                    col_name = data_2.get(f"COL{i}_NAME")
                    value = data_2.get(f"COL{i}_VALUE")

                    if name:  # ignore empty/null columns
                        parameters_2[col_name] = value
                        # print("parameters", parameters)
                        

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
        print("ERROR:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def station_live_values(request, stationNum, id, valve_serial_no):
    if stationNum not in [1, 2]:
        return JsonResponse({"error": "Invalid station"})

    if stationNum == 1:
        data =  get_live_pressure_data1(request, id, valve_serial_no, stationNum)

       
    else:
        data = get_live_pressure_data2(request, id, valve_serial_no, stationNum)

    return JsonResponse({
        "status": "success",
        "station": stationNum,
        "data": data
    })



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


def get_history_prssure_data1(request, testId, valve_serial_no, stationNum):


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




def get_live_pressure_data1(request, id, valve_serial_no, stationNum):

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
        actual_open_degree = getstatus(HmiAddress.S1_ACTUAL_OPEN_DEGREE)
        actual_close_degree =getstatus(HmiAddress.S1_ACTUAL_CLOSE_DEGREE)
        result_value1 = getstatus(HmiAddress.S1_TEST_RESULT)
        actual_bubble = getstatus(HmiAddress.S1_ACTUAL_BUBBLE_COUNT)
        allowed_bubble = getstatus(HmiAddress.S1_SET_BUBBLE_COUNT)
        actual_clamping_psr=getstatus(HmiAddress.S1_ACTUAL_CALMPING_PRESSURE)
        set_clamping_psr = getstatus(HmiAddress.S1_SET_CLAMPING_PRESSURE)
        alarm_msg = getstatus(HmiAddress.S1_ALARM_STATUS)
        
        s1_set_open_torque = getstatus(HmiAddress.S1_SET_OPEN_TORQUE)
        s1_set_close_torque = getstatus(HmiAddress.S1_SET_CLOSE_TORQUE)
        s1_actual_open_torque = getstatus(HmiAddress.S1_ACTUAL_OPEN_TORQUE)
        s1_actual_close_torque = getstatus(HmiAddress.S1_ACTUAL_CLOSE_TORQUE)
        
        # leak_pressure = getstatus(HmiAddress.)

        # Get test mode from HMI
        test_mode = getstatus(HmiAddress.S1_MACHINE_MODE)
        
        # Get alarm name from database
        alarm_name = None
        if alarm_msg is not None:
            with connection.cursor() as cursor:
                cursor.execute("select ALARM_NAME from alarm where ALARM_ID = %s", [alarm_msg])
                alarm_result = cursor.fetchone()
                alarm_name = alarm_result[0] if alarm_result else "Unknown Alarm"
                print(f"Alarm ID: {alarm_msg}, Alarm Name: {alarm_name}")
        else:
            alarm_name = "No Alarm"
            print("No alarm detected")
        # leak_pressure = getstatus(HmiAddress.)
        if value1:
            actual_pre = value1[0]
            actual_timer_status = value1[1]
            actual_time = value1[2]
            result = value1[3]

    return {
        "connected": True,
        "actualPressure": float(actual_pre) if actual_pre is not None else 0.0,
        "time": str(actual_time) if actual_time else "",
        "timerStatus": actual_timer_status,
        "result": result,
        "actual_duration":actual_duration,
        "actual_open_degree": actual_open_degree,
        "actual_close_degree":actual_close_degree,
        "result-value":result_value1,
        "actual_bubbles": actual_bubble,
        "allowed_bubbles": allowed_bubble,
        "actual_clamping_psr":actual_clamping_psr,
        "set_clamping_psr": set_clamping_psr,
        'alarm_msg': alarm_name,
        'test_mode': test_mode,
    
        'set_open_torque': s1_set_open_torque,
        'set_close_torque': s1_set_close_torque,
        'actual_open_torque': s1_actual_open_torque,
        'actual_close_torque': s1_actual_close_torque
    }


def get_live_pressure_data2(request, id, valve_serial_no, stationNum):

    s2_actual_pre = None
    s2_actual_timer_status = None
    s2_actual_time = None
    s2_result = None

    with connection.cursor() as cursor:

        if int(id) == 0:
            cursor.execute("""
                SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
                FROM current_status_station2
                WHERE VALVE_SERIAL_NO = %s
                ORDER BY id DESC
                LIMIT 1
            """, [valve_serial_no])
        else:
            cursor.execute("""
                SELECT PRESSURE, TIMER_STATUS, DATE_TIME, RESULT
                FROM current_status_station2
                WHERE TEST_ID = %s AND VALVE_SERIAL_NO = %s
                ORDER BY id DESC
                LIMIT 1
            """, [id, valve_serial_no])

        value2 = cursor.fetchone()

        s2_actual_duration = getstatus(HmiAddress.S2_ACTUAL_TEST_TIME)
        s2_actual_open_degree = getstatus(HmiAddress.S2_ACTUAL_OPEN_DEGREE)
        s2_actual_close_degree =getstatus(HmiAddress.S2_ACTUAL_CLOSE_DEGREE)
        s2_actual_bubble = getstatus(HmiAddress.S2_ACTUAL_BUBBLE_COUNT)
        s2_actual_clamping_psr=getstatus(HmiAddress.S2_ACTUAL_CALMPING_PRESSURE)
        result_value2 = getstatus(HmiAddress.S2_TEST_RESULT)
        allowed_bubble = getstatus(HmiAddress.S2_SET_BUBBLE_COUNT)
        set_clamping_psr = getstatus(HmiAddress.S2_SET_CLAMPING_PRESSURE)
        alarm_msg = getstatus(HmiAddress.S2_ALARM_STATUS)
        
        s2_set_open_torque = getstatus(HmiAddress.S2_SET_OPEN_TORQUE)
        s2_set_close_torque = getstatus(HmiAddress.S2_SET_CLOSE_TORQUE)
        s2_actual_open_torque = getstatus(HmiAddress.S2_ACTUAL_OPEN_TORQUE)
        s2_actual_close_torque = getstatus(HmiAddress.S2_ACTUAL_CLOSE_TORQUE)
        # leak_pressure = getstatus(HmiAddress.)
        
        s2_set_open_torque = getstatus(HmiAddress.S2_SET_OPEN_TORQUE)
        s2_set_close_torque = getstatus(HmiAddress.S2_SET_CLOSE_TORQUE)
        s2_actual_open_torque = getstatus(HmiAddress.S2_ACTUAL_OPEN_TORQUE)
        s2_actual_close_torque = getstatus(HmiAddress.S2_ACTUAL_CLOSE_TORQUE)

         # Get test mode from HMI
        test_mode = getstatus(HmiAddress.S1_MACHINE_MODE)
        
        # Get alarm name from database
        alarm_name = None
        if alarm_msg is not None:
            with connection.cursor() as cursor:
                cursor.execute("select ALARM_NAME from alarm where ALARM_ID = %s", [alarm_msg])
                alarm_result = cursor.fetchone()
                alarm_name = alarm_result[0] if alarm_result else "Unknown Alarm"
                print(f"Alarm ID: {alarm_msg}, Alarm Name: {alarm_name}")
        else:
            alarm_name = "No Alarm"
            print("No alarm detected")
            
        if value2:
            s2_actual_pre = value2[0]
            s2_actual_timer_status = value2[1]
            s2_actual_time = value2[2]
            s2_result = value2[3]

    return {
        "connected": True,
        "actualPressure": float(s2_actual_pre) if s2_actual_pre is not None else 0.0,
        "time": str(s2_actual_time) if s2_actual_time else "",
        "timerStatus": s2_actual_timer_status,
        "result": s2_result,
        "actual_duration": s2_actual_duration,
        "actual_open_degree": s2_actual_open_degree,
        "actual_close_degree":s2_actual_close_degree,
        "result-value":result_value2,
        "actual_bubbles": s2_actual_bubble,
        "allowed_bubbles": allowed_bubble,
        "actual_clamping_psr":s2_actual_clamping_psr,
        "set_clamping_psr": set_clamping_psr,
        'alarm_msg': alarm_name,
        'test_mode': test_mode,
        'set_open_torque': s2_set_open_torque,
        'set_close_torque': s2_set_close_torque,
        'actual_open_torque': s2_actual_open_torque,
        'actual_close_torque': s2_actual_close_torque
    }
        
    



station1_stop = threading.Event()
station2_stop = threading.Event()

station1_thread = None
station2_thread = None

def store_single_pressure_station1():
    print("Station-1 pressure thread started")

    while not station1_stop.is_set():
        try:
            pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
            timer_status = getstatus(HmiAddress.S1_TIMER_STATUS)
            test_id = getstatus(HmiAddress.S1_TEST_TYPE)

            with connection.cursor() as cursor:
                query = f"""
                        SELECT VALVE_SER_NO, 
                        PRESSURE_UNIT
                        FROM master_temp_data
                        WHERE STATION_STATUS = "Enabled" and ID = 1
                    """
                cursor.execute(query)
                pressure_valveserial = cursor.fetchall()
                print("store pressure value print", pressure_valveserial)

                for row in pressure_valveserial:

                    serial_no = row[0]
                    pressure_unit = row[1].lower()
                    
                    # Read pressure based on unit
                    if  pressure_unit == 'psi':
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                    elif  pressure_unit == 'bar':
                        pressure_bar = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                        pressure = pressure_bar / 10
                    elif  pressure_unit == 'kg/cm2g':
                        pressure_kg = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                        pressure = pressure_kg / 10
                    else:
                        pressure = getstatus(HmiAddress.S1_ACTUAL_PRESSURE)
                
                    # Read other HMI values
                    result =  getstatus(HmiAddress.S1_TEST_RESULT)
                    timer_status = getstatus(HmiAddress.S1_TIMER_STATUS)
                    s1_test_id = getstatus(HmiAddress.S1_TEST_TYPE)

                    query = """
                        SELECT TEST_NAME
                        FROM temp_testing_data_s1
                        WHERE TEST_ID = %s
                    """

                    cursor.execute(query, [s1_test_id])
                    s1_row = cursor.fetchone()

                    if s1_row:
                        s1_test_name =s1_row[0]
                    else:
                        s1_test_name = None


            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO current_status_station1
                    (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [serial_no, test_id, s1_test_name, pressure, timer_status, result])

            
            # print(f"Data stored for S1: Serial={serial_no}, Pressure={pressure}, Test_ID={s1_test_id}, Status={timer_status}")
            print("THREAD ID:", threading.get_ident())

        except Exception as e:
            print("S1 error:", e)

        time.sleep(1)


def store_single_pressure_station2():
    print("Station-2 pressure thread started")

    while not station2_stop.is_set():
        try:
            s2_pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
            s2_timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)

            with connection.cursor() as cursor:
                query = f"""
                        SELECT VALVE_SER_NO, 
                        PRESSURE_UNIT
                        FROM master_temp_data
                        WHERE STATION_STATUS = "Enabled" AND ID=2
                    """
                cursor.execute(query)
                pressure_valveserial_2 = cursor.fetchall()
                print("store pressure value print", pressure_valveserial_2)


                for row2 in pressure_valveserial_2:

                    s2_serial_no = row2[0]
                    s2_pressure_unit = row2[1].lower()
                    # print("pressure unit for live", s2_pressure_unit)
                    
                    # Read pressure based on unit
                    if  s2_pressure_unit == 'psi':
                        s2_pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        print("psi",s2_pressure)
                    elif  s2_pressure_unit == 'bar':
                        pressure_bar = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        s2_pressure = pressure_bar / 10
                        print("bar",s2_pressure)
                    elif  s2_pressure_unit == 'kg/cm2g':
                        pressure_kg = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                        s2_pressure = pressure_kg / 10
                        print("kg",s2_pressure)
                    else:
                        s2_pressure = getstatus(HmiAddress.S2_ACTUAL_PRESSURE)
                
                    # Read other HMI values
                    s2_result =  getstatus(HmiAddress.S2_TEST_RESULT)
                    s2_timer_status = getstatus(HmiAddress.S2_TIMER_STATUS)
                    s2_test_id = getstatus(HmiAddress.S2_TEST_TYPE)

                    query = """
                        SELECT TEST_NAME
                        FROM temp_testing_data_s2
                        WHERE TEST_ID = %s
                    """

                    cursor.execute(query, [s2_test_id])
                    s2_row = cursor.fetchone()

                    if s2_row:
                        s2_test_name = s2_row[0]
                    else:
                        s2_test_name = None


            # with connection.cursor() as cursor:
                cursor.execute("""
                     INSERT INTO current_status_station2
                        (VALVE_SERIAL_NO, TEST_ID, TEST_NAME, PRESSURE, TIMER_STATUS, RESULT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        [s2_serial_no, s2_test_id, s2_test_name, s2_pressure, s2_timer_status, s2_result]
                    )
            # print(f"Data stored for S2: Serial={s2_serial_no}, Pressure={s2_pressure}, Test_ID={s2_test_id}, Status={s2_timer_status}")
            print("THREAD ID:", threading.get_ident())

        except Exception as e:
            print("S2 error:", e)

        time.sleep(1)


def start_single_station_threads(station1_enabled=False, station2_enabled=False):
    global station1_thread, station2_thread

    # Station 1
    if station1_enabled:
        # If thread exists and is alive, but stop flag is set, it's dying. Wait for it.
        if station1_thread and station1_thread.is_alive() and station1_stop.is_set():
            print("Station-1 thread is stopping. Waiting to restart...")
            station1_thread.join()
            station1_thread = None

        # Start if not running
        if not station1_thread or not station1_thread.is_alive():
            station1_stop.clear()
            station1_thread = threading.Thread(
                target=store_single_pressure_station1,
                daemon=True
            )
            station1_thread.start()
            print("Started Station-1 thread")
        else:
            print("Station-1 thread is already running")

    # Station 2
    if station2_enabled:
        # If thread exists and is alive, but stop flag is set, it's dying. Wait for it.
        if station2_thread and station2_thread.is_alive() and station2_stop.is_set():
            print("Station-2 thread is stopping. Waiting to restart...")
            station2_thread.join()
            station2_thread = None

        # Start if not running
        if not station2_thread or not station2_thread.is_alive():
            station2_stop.clear()
            station2_thread = threading.Thread(
                target=store_single_pressure_station2,
                daemon=True
            )
            station2_thread.start()
            print("Started Station-2 thread")
        else:
            print("Station-2 thread is already running")
  


def stop_single_station1():
    global station1_thread
    if station1_thread and station1_thread.is_alive():
        station1_stop.set()
        print("Stopping Station-1 thread")

def stop_single_station2():
    global station2_thread
    if station2_thread and station2_thread.is_alive():
        station2_stop.set()
        print("Stopping Station-2 thread")


# station1_enabled = getstatus(HmiAddress.S1_E_D_STATUS) == 1
# station2_enabled = getstatus(HmiAddress.S2_E_D_STATUS) == 1

# if os.environ.get("RUN_MAIN") == "true":
#     # start_pressure_threads()
#     start_single_station_threads(station1_enabled, station2_enabled)


def save_initial_pressure(request, id, valve_serial_no, stationNum):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
     
    try:
        stationNum = int(stationNum) 

        with connection.cursor() as cursor:

            if stationNum == 1:
                cursor.execute("""
                    UPDATE temp_pressure_analysis
                    SET  START_PRESSURE 
                    WHERE TEST_ID = %s AND VALVE_SER_NO = %s
                """)


    except ValueError:
        return JsonResponse(
            {"error": "Station number must be integer"},
            status=400
        )

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)



@csrf_exempt
def save_final_pressure(request, testId, valve_serial_no, stationNum):

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
        open_degree = body.get("open_degree")
        close_degree = body.get("close_degree")
        pressure_drop = body.get("pressure_drop")
        test_result = body.get("test_result")

        # Convert test_result to status: 1 for PASS, 0 for FAIL
        status = 1 if test_result == "PASS" else 0

        # s1_test_result = getstatus(HmiAddress.S1_TEST_RESULT)
        # print("result value from hmi", s1_test_result)

        # if s1_test_result == 1:
        #     result = "PASS"
        # else:
        #     result = "FAIL"

        if start_pressure is None or end_pressure is None:
            return JsonResponse({"error": "Missing pressure values"},status=400)
        

        with connection.cursor() as cursor:
            if stationNum == 1:
                # First table - includes STATUS field
                cursor.execute("""
                    UPDATE temp_pressure_analysis
                    SET 
                        ACTUAL_PRESSURE = %s,
                        START_PRESSURE  = %s,
                        RESULT_PRESSURE = %s,
                        LEAK_PRESSURE = %s,
                        ACTUAL_TIME=%s,
                        CLAMPING_PRESSURE = %s,
                        ACTUAL_OPEN_TORQUE =%s,
                        ACTUAL_CLOSE_TORQUE = %s,
                        `START` = %s,
                        `END` = %s,
                        VALVE_STATUS = %s,
                        STATUS = %s,
                        DATE_TIME = NOW()
                    WHERE TEST_ID = %s
                    AND VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [
                    result_psr,
                    start_pressure,
                    end_pressure,
                    pressure_drop,
                    actual_time,
                    clampping_psr,
                    open_degree,
                    close_degree,
                    start_time,
                    end_time,
                    test_result,
                    status,
                    testId,
                    valve_serial_no
                ])

                # Second table
                cursor.execute("""
                    UPDATE pressure_analysis
                    SET 
                        ACTUAL_PRESSURE = %s,
                        START_PRESSURE  = %s,
                        RESULT_PRESSURE = %s,
                        LEAK_PRESSURE = %s,
                        ACTUAL_TIME=%s,
                        CLAMPING_PRESSURE = %s,
                        ACTUAL_OPEN_TORQUE =%s,
                        ACTUAL_CLOSE_TORQUE = %s,
                        `START` = %s,
                        `END` = %s,
                        VALVE_STATUS = %s,
                        DATE_TIME = NOW()
                    WHERE TEST_ID = %s
                    AND VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [
                    result_psr,
                    start_pressure,
                    end_pressure,
                    pressure_drop,
                    actual_time,
                    clampping_psr,
                    open_degree,
                    close_degree,
                    start_time,
                    end_time,
                    test_result,
                    testId,
                    valve_serial_no
                ])


            elif stationNum == 2:
                cursor.execute("""
                    UPDATE temp_pressure_analysis
                    SET 
                        ACTUAL_PRESSURE = %s,
                        START_PRESSURE = %s,
                        RESULT_PRESSURE= %s,
                        LEAK_PRESSURE = %s,
                        ACTUAL_TIME=%s,
                        CLAMPING_PRESSURE = %s,
                        ACTUAL_OPEN_TORQUE =%s,
                        ACTUAL_CLOSE_TORQUE = %s,
                        `START` = %s,
                        `END` = %s,
                        VALVE_STATUS = %s,
                        STATUS = %s,
                        DATE_TIME = NOW()
                    WHERE TEST_ID = %s
                    AND VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [
                    result_psr,
                    start_pressure,
                    end_pressure,
                    pressure_drop,
                    actual_time,
                    clampping_psr,
                    open_degree,
                    close_degree,
                    start_time,
                    end_time,
                    test_result,
                    status,
                    testId,
                    valve_serial_no
                ])
                cursor.execute("""
                    UPDATE pressure_analysis
                    SET 
                        ACTUAL_PRESSURE = %s,
                        START_PRESSURE  = %s,
                        RESULT_PRESSURE = %s,
                        LEAK_PRESSURE = %s,
                        ACTUAL_TIME=%s,
                        CLAMPING_PRESSURE = %s,
                        ACTUAL_OPEN_TORQUE =%s,
                        ACTUAL_CLOSE_TORQUE = %s,
                        `START` = %s,
                        `END` = %s,
                        VALVE_STATUS = %s,
                        DATE_TIME = NOW()
                    WHERE TEST_ID = %s
                    AND VALVE_SER_NO = %s
                    AND CYCLE_COMPLETE = 'No'
                """, [
                    result_psr,
                    start_pressure,
                    end_pressure,
                    pressure_drop,
                    actual_time,
                    clampping_psr,
                    open_degree,
                    close_degree,
                    start_time,
                    end_time,
                    test_result,
                    testId,
                    valve_serial_no
                ])
        return JsonResponse({
            "status": "success",
            "message": "Final pressure saved"
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
    

@csrf_exempt
def get_test_result_status(request, stationNum, valve_serial_no):
    """Get test result status for button color coding"""
    
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    try:
        stationNum = int(stationNum)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TEST_ID, STATUS, VALVE_STATUS
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
            """, [valve_serial_no])
            
            rows = cursor.fetchall()
            
            test_statuses = {}
            for row in rows:
                test_id = row[0]
                status = row[1]  # 1 = PASS, 0 = FAIL, NULL = Not completed
                valve_status = row[2]  # "PASS" or "FAIL"
                
                test_statuses[test_id] = {
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

    
def external_abrs_push(serial_no, assembly_no):
    print("[ABRS] Push started")

    try:
        # ---- Push to ABRS (external system) ----
        ABRSService.push_data_to_abrs(serial_no, assembly_no)
        print("[ABRS] Push success")

    except Exception as e:
        print("[ABRS] Push failed:", e)
        return {"success": False, "local": True,"abrs": False,"message": "Stored locally. ABRS push failed"}

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
        return {"local": True,"abrs": True,"message": "Pushed to ABRS, but local status update failed"}

    return { "success": True, "local": True,"abrs": True, "message": "Saved locally & pushed to ABRS"}


def export_station_data_to_e_drive(valve_serial_no, station_num):
    """
    Export current_status_station1 or current_status_station2 table data to E drive as Excel file
    """
    try:
        print(f"[EXPORT_EXCEL] Starting Excel export for valve {valve_serial_no}, station {station_num}")
        
        # Get count id from temp_pressure_analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT_ID
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
            """, [valve_serial_no])
            
            count_row = cursor.fetchone()
            count_id = count_row[0] if count_row else "0"
            print(f"[EXPORT_EXCEL] Count ID: {count_id}")
        
        # Create E drive directory if it doesn't exist
        e_drive_path = "D:/Bray_DB_export"
        os.makedirs(e_drive_path, exist_ok=True)
        print(f"[EXPORT_EXCEL] Export directory: {e_drive_path}")
        
        # Generate filename with serial number and count id
        filename = f"{valve_serial_no}_{count_id}.xlsx"
        filepath = os.path.join(e_drive_path, filename)
        print(f"[EXPORT_EXCEL] Excel file path: {filepath}")
        
        # Determine which table to query based on station number
        station_table = 'current_status_station1' if station_num == 1 else 'current_status_station2'
        print(f"[EXPORT_EXCEL] Querying table: {station_table}")
        
        # Fetch data from database
        with connection.cursor() as cursor:
            query = f"""
                SELECT id, VALVE_SERIAL_NO, PRESSURE, TEST_ID, TEST_NAME,  
                        DATE_TIME, TIMER_STATUS, RESULT
                FROM {station_table}
                WHERE VALVE_SERIAL_NO = %s
                ORDER BY id 
            """
            cursor.execute(query, [valve_serial_no])
            
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            print(f"[EXPORT_EXCEL] Found {len(rows)} data rows")
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"Station {station_num} Data"
        
        # Write headers
        ws.append(columns)
        
        # Write data rows
        for row in rows:
            ws.append(row)
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to E drive
        wb.save(filepath)
        print(f"[EXPORT_EXCEL] Excel file successfully saved: {filepath}")
        
        return True
        
    except Exception as e:
        print(f"[EXPORT_EXCEL] Error exporting Excel file: {e}")
        import traceback
        traceback.print_exc()
        return False
        
        return True
        
    except Exception as e:
        print(f"[EXPORT] Failed to export data: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_test_graph_base64_from_excel(excel_filepath, test_id, test_name):
    """
    Generate pressure vs time graph for a single test from Excel file and return as base64 string
    Returns None if test has no timer on/off events (should be omitted from report)
    """
    try:
        from openpyxl import load_workbook
        from datetime import datetime
        
        # Load the Excel file
        wb = load_workbook(excel_filepath)
        ws = wb.active
        
        # Read data from Excel
        date_times = []
        pressures = []
        timer_status = []
        
        # Skip header row, start from row 2
        for row in ws.iter_rows(min_row=2, values_only=True):
            # Columns: id, VALVE_SERIAL_NO, PRESSURE, TEST_ID, TEST_NAME, DATE_TIME, TIMER_STATUS, RESULT
            if row[3] == test_id:  # TEST_ID column
                date_time = row[5]  # DATE_TIME column
                pressure = row[2]   # PRESSURE column
                timer_stat = row[6] # TIMER_STATUS column
                
                if date_time and pressure is not None:
                    # Convert datetime to proper format if it's a string
                    if isinstance(date_time, str):
                        try:
                            date_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                        except:
                            continue
                    
                    date_times.append(date_time)
                    pressures.append(float(pressure))
                    timer_status.append(int(timer_stat) if timer_stat is not None else 0)
        
        if not date_times:
            print(f"[GRAPH] No data found for test {test_id} in Excel file")
            wb.close()
            return None
        
        # Check if test has timer on/off events
        has_timer_on = any(status == 1 for status in timer_status)
        has_timer_off_after_on = False
        
        timer_was_on = False
        for status in timer_status:
            if status == 1:
                timer_was_on = True
            elif status == 0 and timer_was_on:
                has_timer_off_after_on = True
                break
        
        # If no timer events, skip this test (return None to omit from report)
        if not has_timer_on or not has_timer_off_after_on:
            print(f"[GRAPH] Test {test_id} ({test_name}) has no complete timer on/off cycle - omitting from report")
            wb.close()
            return None
        
        # Create the graph
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot the pressure line
        ax.plot(date_times, pressures, 'b-', linewidth=2, label='Pressure')
        
        # Find where TIMER_STATUS changes from 0 to 1 (green line)
        # and from 1 to 0 (red line)
        green_line_drawn = False
        red_line_drawn = False
        
        for i in range(len(timer_status)):
            # Draw green line when first 1 is found
            if timer_status[i] == 1 and not green_line_drawn:
                ax.axvline(x=date_times[i], color='green', linestyle='--', 
                          linewidth=2, label='Timer Start')
                green_line_drawn = True
            
            # Draw red line when 0 is found after 1
            if green_line_drawn and timer_status[i] == 0 and not red_line_drawn:
                ax.axvline(x=date_times[i], color='red', linestyle='--', 
                          linewidth=2, label='Timer Stop')
                red_line_drawn = True
                break
        
        # Format the plot
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Pressure', fontsize=12)
        ax.set_title(f'{test_name}', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Format x-axis to show time nicely
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        
        # Tight layout to prevent label cutoff
        plt.tight_layout()
        
        # Save to BytesIO buffer instead of file
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        # Convert to base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        plt.close(fig)
        buffer.close()
        wb.close()
    
        return f"data:image/png;base64,{image_base64}"
        
    except Exception as e:
        print(f"[GRAPH] Error generating graph from Excel for test {test_id}: {e}")
        import traceback
        traceback.print_exc()
        return None



def export_merged_report_to_e_drive(valve_serial_no, station_num):
    """
    Export merged_report.html with test data to E drive as PDF - one page per test
    """
    try:        
        print(f"[EXPORT_PDF] Starting PDF export for valve {valve_serial_no}, station {station_num}")
        
        # Get count id from temp_pressure_analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT_ID
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
                ORDER BY COUNT_ID DESC
                LIMIT 1
            """, [valve_serial_no])
            
            count_row = cursor.fetchone()
            count_id = count_row[0] if count_row else "0"
            print(f"[EXPORT_PDF] Count ID: {count_id}")
            
            # Fetch master data for the valve (common for all tests)
            cursor.execute("""
                SELECT VALVE_SER_NO, SIZE_NAME, COL4_VALUE,
                       COL7_VALUE, COL8_VALUE
                FROM master_temp_data
                WHERE VALVE_SER_NO = %s
            """, [valve_serial_no])
            
            master_row = cursor.fetchone()
            if not master_row:
                print(f"[EXPORT_PDF] No master data found for valve {valve_serial_no}")
                return False
            
            
            serial_no = master_row[0] or ""
            valve_size = master_row[1] or ""
            part_no = master_row[2] or ""
            assembled_by = master_row[3] or ""
            tested_by = master_row[4] or ""
            
            # Fetch ALL test data from pressure_analysis (not just one)
            cursor.execute("""
                SELECT TEST_ID, TEST_NAME, SET_TIME, SET_PRESSURE, 
                       PRESSURE_UNIT, START, END, VALVE_STATUS
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
                ORDER BY TEST_ID ASC
            """, [valve_serial_no])
            
            test_rows = cursor.fetchall()
            print(f"[EXPORT_PDF] Found {len(test_rows)} test records")
            
            if not test_rows:
                print(f"[EXPORT_PDF] No test data found for valve {valve_serial_no}")
                return False
        
        # Get report path from configuration_table or use default
        default_path = "D:/Bray_Reports"
        base_report_path = default_path
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT REPORT_PATH FROM configuration_table")
            path_row = cursor.fetchone()
            
            # Check if database path exists and is valid
            if path_row and path_row[0] and path_row[0].strip():
                configured_path = path_row[0].strip()
                print(f"[EXPORT_PDF] Configured report path: {configured_path}")
                
                # Check if the drive/path is accessible
                try:
                    # Extract drive letter from the configured path
                    drive = os.path.splitdrive(configured_path)[0]
                    
                    # Check if drive exists (for Windows)
                    if drive and not os.path.exists(drive + "/"):
                        print(f"[EXPORT_PDF] Configured drive {drive} not accessible, using default")
                        base_report_path = default_path
                    else:
                        base_report_path = configured_path
                except Exception as e:
                    print(f"[EXPORT_PDF] Error checking configured path: {e}")
                    base_report_path = default_path
            else:
                print(f"[EXPORT_PDF] No path configured, using default: {default_path}")
        
        print(f"[EXPORT_PDF] Using report path: {base_report_path}")
        
        # Create pdf subfolder inside the report path
        pdf_folder_path = os.path.join(base_report_path, "pdf")
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(pdf_folder_path, exist_ok=True)
            print(f"[EXPORT_PDF] PDF folder created/verified: {pdf_folder_path}")
        except Exception as e:
            # Fallback to default path with pdf subfolder
            print(f"[EXPORT_PDF] Error creating PDF folder, using fallback: {e}")
            base_report_path = default_path
            pdf_folder_path = os.path.join(base_report_path, "pdf")
            os.makedirs(pdf_folder_path, exist_ok=True)
            print(f"[EXPORT_PDF] Fallback PDF folder: {pdf_folder_path}")

        # Get current date
        from datetime import datetime
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Get the Excel file path (should be in D:/Bray_DB_export)
        excel_filename = f"{valve_serial_no}_{count_id}.xlsx"
        excel_filepath = os.path.join("D:/Bray_DB_export", excel_filename)
        print(f"[EXPORT_PDF] Looking for Excel file: {excel_filepath}")
        
        # Check if Excel file exists
        if not os.path.exists(excel_filepath):
            print(f"[EXPORT_PDF] Excel file not found: {excel_filepath}")
            return False
        
        print(f"[EXPORT_PDF] Excel file found, proceeding with graph generation")
        
        # Build HTML content with all test pages
        all_pages_html = ""
        valid_tests = []
        
        # First pass: identify valid tests (those with timer events)
        for test_row in test_rows:
            test_id = test_row[0]
            test_type = test_row[1] or ""
            print(f"[EXPORT_PDF] Processing test {test_id} ({test_type})")
            
            # Generate graph from Excel file to check if test is valid
            graph_image_base64 = generate_test_graph_base64_from_excel(
                excel_filepath, test_id, test_type
            )
            
            # Only include tests that have timer on/off events
            if graph_image_base64 is not None:
                valid_tests.append((test_row, graph_image_base64))
                print(f"[EXPORT_PDF] Test {test_id} ({test_type}) - valid, graph generated")
            else:
                print(f"[EXPORT_PDF] Skipping test {test_id} ({test_type}) - no timer events")
        
        # Check if we have any valid tests to include in the report
        if len(valid_tests) == 0:
            print(f"[EXPORT_PDF] No valid tests found for valve {valve_serial_no} - no PDF report generated")
            return False
        
        print(f"[EXPORT_PDF] Found {len(valid_tests)} valid tests for PDF generation")
        
        # Second pass: generate HTML for valid tests
        for idx, (test_row, graph_image_base64) in enumerate(valid_tests):
            test_id = test_row[0]
            test_type = test_row[1] or ""
            set_time = test_row[2] if test_row[2] else "0"
            set_pressure = test_row[3] if test_row[3] else "0"
            pressure_unit = test_row[4] if test_row[4] else "bar"
            start_time_raw = test_row[5]
            end_time_raw = test_row[6]
            valve_status = test_row[7] if test_row[7] else "UNKNOWN"
            
            # Format start and end times - extract only time portion
            start_time = ""
            end_time = ""
            
            if start_time_raw:
                if isinstance(start_time_raw, str):
                    # If it's already a string, extract only time portion
                    start_time = start_time_raw
                else:
                    # If it's a datetime object, format to HH:MM:SS
                    start_time = start_time_raw.strftime("%H:%M:%S")
            
            if end_time_raw:
                if isinstance(end_time_raw, str):
                    end_time = end_time_raw
                else:
                    end_time = end_time_raw.strftime("%H:%M:%S")
            
            # Calculate time difference
            time_diff = ""
            if start_time and end_time:
                try:
                    from datetime import datetime
                    start_dt = datetime.strptime(start_time, "%H:%M:%S")
                    end_dt = datetime.strptime(end_time, "%H:%M:%S")
                    diff = end_dt - start_dt
                    time_diff = str(diff)
                except Exception as e:
                    time_diff = "N/A"
            
            # Prepare context data for this test
            context = {
                'serial_no': serial_no,
                'valve_size': valve_size,
                'part_no': part_no,
                'tested_by': tested_by,
                'test_date': current_date,
                'test_type': test_type,
                'set_time': set_time,
                'set_pressure': set_pressure,
                'pressure_unit': pressure_unit,
                'start_time': start_time,
                'end_time': end_time,
                'time_diff': time_diff,
                'valve_status': valve_status,
                'current_date': current_date,
                'graph_image_base64': graph_image_base64
            }
            
            # Render the template for this test
            page_html = render_to_string('merged_report.html', context)
            
            # Add page break after each page except the last one
            if idx < len(valid_tests) - 1:
                # Add page break style to the body tag
                page_html = page_html.replace('</body>', '<div style="page-break-after: always;"></div></body>')
            
            all_pages_html += page_html
        
        # Generate filename with serial number and count id
        filename = f"{valve_serial_no}_{count_id}_report.pdf"
        filepath = os.path.join(pdf_folder_path, filename)
        print(f"[EXPORT_PDF] Generating PDF: {filepath}")
        
        # Convert combined HTML to PDF using weasyprint
        HTML(string=all_pages_html).write_pdf(filepath)
        print(f"[EXPORT_PDF] PDF successfully generated: {filepath}")
        
        return True
        
    except Exception as e:
        print(f"[EXPORT_PDF] Error generating PDF report: {e}")
        import traceback
        traceback.print_exc()
        return False


def copy_excel_template_to_report_path(valve_serial_no, station_num):
    """
    Copy Excel template from bray_app/excel to the excel subfolder in report path
    """
    try:
        print(f"[EXCEL_COPY] Starting Excel template copy for valve {valve_serial_no}, station {station_num}")
        import shutil
        today_date = datetime.now().strftime("%d-%m-%Y")
        
        # Get count id from temp_pressure_analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT_ID
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
                ORDER BY COUNT_ID DESC
                LIMIT 1
            """, [valve_serial_no])
            
            count_row = cursor.fetchone()
            count_id = count_row[0] if count_row else "0"
            print(f"[EXCEL_COPY] Count ID: {count_id}")
        
        # Get report path from configuration_table or use default
        default_path = "D:/Bray_Reports"
        base_report_path = default_path
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT REPORT_PATH FROM configuration_table")
            path_row = cursor.fetchone()
            
            # Check if database path exists and is valid
            if path_row and path_row[0] and path_row[0].strip():
                configured_path = path_row[0].strip()
                
                # Check if the drive/path is accessible
                try:
                    # Extract drive letter from the configured path
                    drive = os.path.splitdrive(configured_path)[0]
                    
                    # Check if drive exists (for Windows)
                    if drive and not os.path.exists(drive + "/"):
                        base_report_path = default_path
                    else:
                        base_report_path = configured_path
                except Exception as e:
                    base_report_path = default_path
            else:
                print(f"[EXCEL_COPY] No path configured, using default: {default_path}")
        
        # Create excel subfolder inside the report path
        excel_folder_path = os.path.join(base_report_path, "excel")
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(excel_folder_path, exist_ok=True)
        except Exception as e:
            # Fallback to default path with excel subfolder
            base_report_path = default_path
            excel_folder_path = os.path.join(base_report_path, "excel")
            os.makedirs(excel_folder_path, exist_ok=True)
        
        # Source Excel template path (inside bray_app)
        source_excel_path = os.path.join("bray_app", "excel", "Bray_Excel_Report_20122024_20_12_2024_11_36.xlsx")
        print(f"[EXCEL_COPY] Source template path: {source_excel_path}")
        
        # Check if source file exists
        if not os.path.exists(source_excel_path):
            print(f"[EXCEL_COPY] Source template file not found: {source_excel_path}")
            return False
        
        # Destination filename with valve serial and count id
        destination_filename = f"{valve_serial_no}_{count_id}_template.xlsx"
        destination_filepath = os.path.join(excel_folder_path, destination_filename)
        print(f"[EXCEL_COPY] Destination path: {destination_filepath}")
        
        # Copy the Excel template
        shutil.copy2(source_excel_path, destination_filepath)
        print(f"[EXCEL_COPY] Template file copied successfully")
        
        # Fetch component data from master_temp_data using the current valve serial number
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT VALVE_SER_NO,COL5_VALUE,COL9_VALUE,COL10_VALUE,COL11_VALUE,
                COL12_VALUE,COL13_VALUE,COL14_VALUE,
                COL15_VALUE,COL16_VALUE,COL17_VALUE, 
                COL18_VALUE,COL19_VALUE,COL20_VALUE,
                COL21_VALUE,COL22_VALUE,COL23_VALUE,COL7_VALUE,COL8_VALUE,COL4_VALUE
                FROM master_temp_data
                WHERE VALVE_SER_NO = %s
            """, [valve_serial_no])
            
            serial_data = cursor.fetchone()
            
            if not serial_data:
                # Fallback to using the parameter valve serial number
                valve_serial_from_db = valve_serial_no
                Bray_Order = ""
                Body_Part_No = ""
                Body_Heat_No = ""
                Body_Material_No = ""
                Bottom_Part_No = ""
                Bottom_Heat_No = ""
                Bottom_Material_No = ""
                Disc_Part_No = ""
                Disc_Heat_No = ""
                Disc_Material_No = ""
                Seat_Part_No = ""
                Seat_Heat_No = ""
                Seat_Material_No = ""
                Stem_Part_No = ""
                Stem_Heat_No = ""
                Stem_Material_No = ""
                Bray_Part_No = ""
            else:
                valve_serial_from_db = serial_data[0] or valve_serial_no  # Use parameter as fallback
                Bray_Order = serial_data[1] or ""
                Body_Part_No = serial_data[2] or ""
                Body_Heat_No = serial_data[3] or ""
                Body_Material_No = serial_data[4] or ""
                Bottom_Part_No = serial_data[5] or ""
                Bottom_Heat_No = serial_data[6] or ""
                Bottom_Material_No = serial_data[7] or ""
                Disc_Part_No = serial_data[8] or ""
                Disc_Heat_No = serial_data[9] or ""
                Disc_Material_No = serial_data[10] or ""
                Seat_Part_No = serial_data[11] or ""
                Seat_Heat_No = serial_data[12] or ""
                Seat_Material_No = serial_data[13] or ""
                Stem_Part_No = serial_data[14] or ""
                Stem_Heat_No = serial_data[15] or ""
                Stem_Material_No = serial_data[16] or ""
                assembled_by = serial_data[17] or ""
                tested_by = serial_data[18] or ""
                Bray_Part_No = serial_data[19] or ""
            
        # Fetch test results from abrs_result_status using the current valve serial number
        with connection.cursor() as cursor:
            cursor.execute(""" 
                SELECT COL1_VALUE,COL2_VALUE,COL3_VALUE,COL4_VALUE,COL5_VALUE,COL6_VALUE,COL7_VALUE,COL8_VALUE,
                       COL9_VALUE,COL10_VALUE,COL11_VALUE,COL12_VALUE,COL13_VALUE 
                FROM abrs_result_status 
                WHERE SERIAL_NO = %s 
            """, [valve_serial_no])
            
            result_data = cursor.fetchone()
            
            # Get cycle test status based on station number
            if station_num == 1:
                Valve_Cycle_Test = getstatus(HmiAddress.S1_CYCLE_TEST_STATUS)
            else:  # station_num == 2
                Valve_Cycle_Test = getstatus(HmiAddress.S2_CYCLE_TEST_STATUS)
                
            if Valve_Cycle_Test == 1:
                Valve_Cycle_Test = "Yes"
            else:
                Valve_Cycle_Test = "No"
            
            if not result_data:
                print(f"[EXCEL_COPY] No test results found in abrs_result_status for valve serial: {valve_serial_no}")
                # Set default empty values
                OPEN_TORQUE = ""
                CLOSE_TORQUE = ""
                VALVE_CYCLE_TEST = ""
                HYDROSHELL_TEST_RESULT = ""
                HYDROSHELL_TEST_DURATION = ""
                HYDROSEAT_P_TEST_RESULT = ""
                HYDROSEAT_P_TEST_DURATION = ""
                HYDROSEAT_N_TEST_RESULT = ""
                HYDROSEAT_N_TEST_DURATION = ""
                AIRSEAT_P_TEST_RESULT = ""
                AIRSEAT_P_TEST_DURATION = ""
                AIRSEAT_N_TEST_RESULT = ""
                AIRSEAT_N_TEST_DURATION = ""
            else:
                OPEN_TORQUE = result_data[0] or ""
                CLOSE_TORQUE = result_data[1] or ""
                VALVE_CYCLE_TEST = Valve_Cycle_Test or ""
                HYDROSHELL_TEST_RESULT = result_data[3] or ""
                HYDROSHELL_TEST_DURATION = result_data[4] or ""
                HYDROSEAT_P_TEST_RESULT = result_data[5] or ""
                HYDROSEAT_P_TEST_DURATION = result_data[6] or ""
                HYDROSEAT_N_TEST_RESULT = result_data[7] or ""
                HYDROSEAT_N_TEST_DURATION = result_data[8] or ""
                AIRSEAT_P_TEST_RESULT = result_data[9] or ""
                AIRSEAT_P_TEST_DURATION = result_data[10] or ""
                AIRSEAT_N_TEST_RESULT = result_data[11] or ""
                AIRSEAT_N_TEST_DURATION = result_data[12] or ""

        # Load the Excel workbook to populate data
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(destination_filepath)
            worksheet = workbook.active  # Use the active sheet
            
            # Put valve serial number in cell H12
            worksheet.cell(row=12, column=8, value=valve_serial_from_db)  # H12 (row=12, column=8 for H)
            worksheet.cell(row=12, column=3, value=Bray_Order)  
            worksheet.cell(row=5, column=3, value=Body_Part_No) 
            worksheet.cell(row=5, column=6, value=Body_Heat_No) 
            worksheet.cell(row=5, column=9, value=Body_Material_No) 
            worksheet.cell(row=6, column=3, value=Bottom_Part_No) 
            worksheet.cell(row=6, column=6, value=Bottom_Heat_No) 
            worksheet.cell(row=6, column=9, value=Bottom_Material_No)
            worksheet.cell(row=7, column=3, value=Disc_Part_No) 
            worksheet.cell(row=7, column=6, value=Disc_Heat_No) 
            worksheet.cell(row=7, column=9, value=Disc_Material_No)
            worksheet.cell(row=8, column=3, value=Seat_Part_No) 
            worksheet.cell(row=8, column=6, value=Seat_Heat_No) 
            worksheet.cell(row=8, column=9, value=Seat_Material_No)
            worksheet.cell(row=9, column=3, value=Stem_Part_No) 
            worksheet.cell(row=9, column=6, value=Stem_Heat_No) 
            worksheet.cell(row=9, column=9, value=Stem_Material_No)
            worksheet.cell(row=28, column=10, value=assembled_by)
            worksheet.cell(row=29, column=10, value=tested_by)
            worksheet.cell(row=11, column=4, value=Bray_Part_No)
            worksheet.cell(row=13, column=3, value=today_date)
            worksheet.cell(row=13, column=8, value='No Leak Observed')
            
            worksheet.cell(row=16, column=10, value=OPEN_TORQUE)
            worksheet.cell(row=17, column=10, value=CLOSE_TORQUE)
            worksheet.cell(row=15, column=10, value=VALVE_CYCLE_TEST)
            worksheet.cell(row=18, column=10, value=HYDROSHELL_TEST_RESULT)
            worksheet.cell(row=19, column=10, value=HYDROSHELL_TEST_DURATION)
            worksheet.cell(row=20, column=10, value=HYDROSEAT_P_TEST_RESULT)
            worksheet.cell(row=21, column=10, value=HYDROSEAT_P_TEST_DURATION)
            worksheet.cell(row=22, column=10, value=HYDROSEAT_N_TEST_RESULT)
            worksheet.cell(row=23, column=10, value=HYDROSEAT_N_TEST_DURATION)
            worksheet.cell(row=24, column=10, value=AIRSEAT_P_TEST_RESULT)
            worksheet.cell(row=25, column=10, value=AIRSEAT_P_TEST_DURATION)
            worksheet.cell(row=26, column=10, value=AIRSEAT_N_TEST_RESULT)
            worksheet.cell(row=27, column=10, value=AIRSEAT_N_TEST_DURATION)
            

            # Save the populated workbook
            workbook.save(destination_filepath)
            workbook.close()
            
            print(f"[EXCEL_COPY] Excel template populated with valve serial '{valve_serial_from_db}' in H12: {destination_filepath}")
            
        except Exception as e:
            print(f"[EXCEL_COPY] Failed to populate Excel template: {e}")
            import traceback
            traceback.print_exc()
            print(f"[EXCEL_COPY] Excel template copied successfully (without population): {destination_filepath}")
            # Still return True as the file was copied successfully
            return True
        
        print(f"[EXCEL_COPY] Excel template copied and populated successfully: {destination_filepath}")
        return True
        
    except Exception as e:
        print(f"[EXCEL_COPY] Failed to copy Excel template: {e}")
        import traceback
        traceback.print_exc()
        return False


@csrf_exempt
def cycle_complete(request, stationNum, valveSerial):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        # print(f"[CYCLE_COMPLETE] Starting cycle complete for Station {stationNum}, Valve {valveSerial}")
        stationNum = int(stationNum)    
        
        # Check pressure drain and cycle test status before allowing cycle complete
        s1_pressure_drain_status = getstatus(HmiAddress.S1_PRESSURE_DRAIN) 
        s1_cycle_start_stop_status = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)
        
        s2_pressure_drain_status = getstatus(HmiAddress.S2_PRESSURE_DRAIN) 
        s2_cycle_start_stop_status = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS)
        
        print(f"[CYCLE_COMPLETE] S1 Pressure Drain: {s1_pressure_drain_status}, S1 Cycle Status: {s1_cycle_start_stop_status}")
        print(f"[CYCLE_COMPLETE] S2 Pressure Drain: {s2_pressure_drain_status}, S2 Cycle Status: {s2_cycle_start_stop_status}")
        
        # Check based on which station is being completed
        if stationNum == 1:
            if s1_pressure_drain_status != 0 or s1_cycle_start_stop_status != 0:
                return JsonResponse({
                    "success": False,
                    "message": "Cannot complete cycle. Pressure drain or cycle test is still in progress at Station1."
                }, status=400)
        elif stationNum == 2:
            if s2_pressure_drain_status != 0 or s2_cycle_start_stop_status != 0:
                return JsonResponse({
                    "success": False,
                    "message": "Cannot complete cycle. Pressure drain or cycle test is still in progress at Station2."
                }, status=400)
            
        # Get the test IDs that are actually enabled for this valve
        with connection.cursor() as cursor:
            cursor.execute("SELECT TEST_ID FROM temp_pressure_analysis WHERE VALVE_SER_NO = %s", [valveSerial])
            test_rows = cursor.fetchall()            
            enabled_test_ids = [row[0] for row in test_rows]
            print(f"[CYCLE_COMPLETE] Found enabled test IDs: {enabled_test_ids}")
            
        # Map test IDs to their HMI status addresses based on station
        if stationNum == 1:
            test_id_to_status = {
                1: ('S1_HYDRO_SHELL_TEST_STATUS', HmiAddress.S1_HYDRO_SHELL_TEST_STATUS),
                2: ('S1_HYDRO_SEAT_P_TEST_STATUS', HmiAddress.S1_HYDRO_SEAT_P_TEST_STATUS),
                3: ('S1_HYDRO_SEAT_N_TEST_STATUS', HmiAddress.S1_HYDRO_SEAT_N_TEST_STATUS),
                4: ('S1_AIR_SEAT_P_TEST_STATUS', HmiAddress.S1_AIR_SEAT_P_TEST_STATUS),
                5: ('S1_AIR_SEAT_N_TEST_STATUS', HmiAddress.S1_AIR_SEAT_N_TEST_STATUS)
            }
        else:  # stationNum == 2
            test_id_to_status = {
                1: ('S2_HYDRO_SHELL_TEST_STATUS', HmiAddress.S2_HYDRO_SHELL_TEST_STATUS),
                2: ('S2_HYDRO_SEAT_P_TEST_STATUS', HmiAddress.S2_HYDRO_SEAT_P_TEST_STATUS),
                3: ('S2_HYDRO_SEAT_N_TEST_STATUS', HmiAddress.S2_HYDRO_SEAT_N_TEST_STATUS),
                4: ('S2_AIR_SEAT_P_TEST_STATUS', HmiAddress.S2_AIR_SEAT_P_TEST_STATUS),
                5: ('S2_AIR_SEAT_N_TEST_STATUS', HmiAddress.S2_AIR_SEAT_N_TEST_STATUS)
            }
        
        skip_reports = False
        for test_id in enabled_test_ids:
            if test_id in test_id_to_status:
                status_name, status_address = test_id_to_status[test_id]
                test_status = getstatus(status_address)
                print(f"[CYCLE_COMPLETE] Test ID {test_id} ({status_name}): status = {test_status}")
                
                # If any enabled test failed (status = 0), skip reports
                if test_status == 0:
                    skip_reports = True
                    print(f"[CYCLE_COMPLETE] Test ID {test_id} failed, skipping reports")
                    break
        
        print(f"[CYCLE_COMPLETE] Skip reports: {skip_reports}")
        
        if not skip_reports:
            # STEP 1: Export Excel file FIRST (PDF generation depends on it)
            print("[CYCLE_COMPLETE] Starting Excel export...")
            excel_success = export_station_data_to_e_drive(valveSerial, stationNum)
            print(f"[CYCLE_COMPLETE] Excel export result: {excel_success}")
            
            # STEP 2: Copy Excel template to report path
            if excel_success:
                print("[CYCLE_COMPLETE] Starting Excel template copy...")
                template_success = copy_excel_template_to_report_path(valveSerial, stationNum)
                print(f"[CYCLE_COMPLETE] Excel template copy result: {template_success}")
            
            # STEP 3: Export PDF report AFTER Excel file is created
            if excel_success:
                print("[CYCLE_COMPLETE] Starting PDF report generation...")
                report_success = export_merged_report_to_e_drive(valveSerial, stationNum)
                print(f"[CYCLE_COMPLETE] PDF report generation result: {report_success}")
            else:
                print("[CYCLE_COMPLETE] Skipping PDF generation due to Excel export failure")
        else:
            print("[CYCLE_COMPLETE] Skipping report generation due to test failure(s)")
        
        with connection.cursor() as cursor:

            #Fetch ALL pending tests BEFORE marking cycle complete
            cursor.execute("""
                SELECT TEST_ID
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
            """, [valveSerial])

            test_rows = cursor.fetchall()

            #Push each test to ABRS
            for (test_id,) in test_rows:
                internal_abrs_push(valveSerial, test_id)

            # Update STATUS to 0 for all tests when cycle completes
            cursor.execute("""
                UPDATE temp_pressure_analysis
                SET STATUS = 0
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
            """, [valveSerial])

            #Now mark cycle complete
            cursor.execute("""
                UPDATE pressure_analysis
                SET CYCLE_COMPLETE = 'Yes'
                WHERE VALVE_SER_NO = %s
            """, [valveSerial])

            cursor.execute("select Serial_No from serial_tbl where Serial_No = %s", [valveSerial])
            row = cursor.fetchone()
            if row:
                cursor.execute("update serial_tbl set Count_No = Count_No + 1 where Serial_No = %s", [valveSerial])
            else:   
                cursor.execute("insert into serial_tbl (Serial_No, Count_No) values (%s, %s)", [valveSerial, 1])

            #Station specific cleanup
            if stationNum == 1:
                cursor.execute("""
                    UPDATE master_temp_data
                    SET STATION_STATUS = 'Disabled'
                    WHERE ID = 1
                """)

                cursor.execute("""
                    DELETE FROM temp_testing_data_s1
                    WHERE VALVE_SERIAL_NO = %s
                """, [valveSerial])

                cursor.execute("""
                    DELETE FROM temp_pressure_analysis
                    WHERE VALVE_SER_NO = %s
                """, [valveSerial])
                # cursor.execute("""
                #     TRUNCATE TABLE temp_testing_data_s1
                #     """)

                # cursor.execute("""
                #     TRUNCATE TABLE temp_pressure_analysis
                #     """)

                # write_to_hmi(HmiAddress.S1_E_D_STATUS, 0)
                # write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
                # write_to_hmi(HmiAddress.S1_HIM_TEST_TYPE, 0)
                
                # Set all S1 HMI addresses to 0 (addresses 2000-2036)
                # for address in range(2000, 2045):
                #     write_to_hmi(address, 0)

                write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
                write_to_hmi(HmiAddress.S1_VALVE_SIZE, 0)
                write_to_hmi(HmiAddress.S1_VALVE_CLASS, 0)
                write_to_hmi(HmiAddress.S1_SET_PRESSURE, 0)
                write_to_hmi(HmiAddress.S1_SET_HOLDING_TIME, 0)
                    
                stop_single_station1()
                clear_station_1()

            elif stationNum == 2:
                cursor.execute("""
                    UPDATE master_temp_data
                    SET STATION_STATUS = 'Disabled'
                    WHERE ID = 2
                """)
                
                # Use DELETE with WHERE clause for consistency and safety
                cursor.execute("""       
                    DELETE FROM temp_testing_data_s2
                    WHERE VALVE_SERIAL_NO = %s
                    """,[valveSerial]
                )
                cursor.execute("""
                    DELETE FROM temp_pressure_analysis
                    WHERE VALVE_SER_NO = %s
                """,[valveSerial]
                )
                
                # Reset all S2 HMI addresses to 0 (addresses 3000-3044) for consistency with S1
                # for address in range(2100, 2150):
                #     write_to_hmi(address, 0)

                write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
                write_to_hmi(HmiAddress.S2_VALVE_SIZE, 0)
                write_to_hmi(HmiAddress.S2_VALVE_CLASS, 0)
                write_to_hmi(HmiAddress.S2_SET_PRESSURE, 0)
                write_to_hmi(HmiAddress.S2_SET_HOLDING_TIME, 0)
                    
                stop_single_station2()
                clear_station_2()

            else:
                return JsonResponse({"error": "Invalid station number"},status=400)
            
            # ---------- STEP 2: ABRS PUSH (NO DB TX) ----------
            cursor.execute("""
                SELECT ASSEMBLY_NO
                FROM abrs_result_status
                WHERE SERIAL_NO = %s
            """, [valveSerial])

            row = cursor.fetchone()

        if not row:
            return JsonResponse({"success": False, "abrs": False,"message": "Saved locally (assembly missing)"})
        
        abrs_response = external_abrs_push(valveSerial, row[0])

        return JsonResponse(abrs_response)

    except Exception as e:
        return JsonResponse({"status": "error", "success": False, "message": str(e)}, status=500)


@csrf_exempt
def get_pressure_history(request):
    """Get all pressure history for a specific test_id"""
    test_id = request.GET.get('test_id', None)
    
    if test_id is None:
        return JsonResponse({
            "status": "error",
            "message": "test_id parameter is required"
        })
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT Pressure, Timer_status, created_time, test_completed 
                   FROM current_status_station1 
                   WHERE TestName = %s 
                   ORDER BY id ASC""",
                [test_id]
            )
            records = cursor.fetchall()
        
        # Format the records for the frontend
        pressure_history = []
        for record in records:
            pressure_history.append({
                'pressure': float(record[0]) if record[0] is not None else 0.0,
                'timer_status': record[1],
                'time': str(record[2]) if record[2] else "",
                'result': record[3]
            })
        
        return JsonResponse({
            "status": "success",
            "pressure_history": pressure_history
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })
    


def auto_test_select(request, stationNum):

    if stationNum not in [1, 2]:
        return JsonResponse({
            "status": "error",
            "message": "Invalid station number"
        }, status=400)

    if stationNum == 1:

        data = start_auto_test_station1(stationNum)

    if stationNum == 2:

        data = start_auto_test_station2(stationNum)
            
    return JsonResponse({
        "status": "success",
        **data
    })
   

def start_auto_test_station1(stationNum):

    # --- Read HMI ---
    s1_machine_mode     = getstatus(HmiAddress.S1_MACHINE_MODE)       # 0=Auto
    s1_test_type        = getstatus(HmiAddress.S1_TEST_TYPE)
    s1_hmi_test_type    = getstatus(HmiAddress.S1_HIM_TEST_TYPE)
    s1_cycle_complete   = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)

    response = {
        "station_enabled": True,
        "machine_mode": s1_machine_mode,
        "s1_test_id": None,
        "cycle_complete": False,
        "test_changed": False
    }

    # MANUAL MODE → do nothing
    if s1_machine_mode != 0:
        return response

    # AUTO MODE
    response["s1_test_id"] = s1_test_type

    #CYCLE COMPLETE
    if s1_cycle_complete == 0:
        if  s1_hmi_test_type == 0:
            print("[NON-SYNC STATION 1][AUTO] Cycle completed")
            response["cycle_complete"] = True
            # Reset test type register
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)

    # TEST CHANGE
    if s1_cycle_complete == 1 and s1_hmi_test_type != s1_test_type:
    # if s1_hmi_test_type != s1_test_type:
        print(f"[AUTO][S1] Test changed → {s1_hmi_test_type}")

        write_to_hmi(HmiAddress.S1_TEST_TYPE, s1_hmi_test_type)

        response["test_changed"] = True
        response["test_id"] = s1_hmi_test_type

    return response



def start_auto_test_station2(stationNum):

     # --- Read HMI ---
    s2_machine_mode     = getstatus(HmiAddress.S2_MACHINE_MODE)       
    s2_test_type        = getstatus(HmiAddress.S2_TEST_TYPE)
    s2_hmi_test_type    = getstatus(HmiAddress.S2_HIM_TEST_TYPE)
    s2_cycle_complete   = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS)

    response = {
        "station_enabled": True,
        "machine_mode": s2_machine_mode,
        "s2_test_id": None,
        "cycle_complete": False,
        "test_changed": False
    }

    # MANUAL MODE → do nothing
    if s2_machine_mode != 0:
        return response

    # AUTO MODE
    response["s2_test_id"] = s2_test_type

    #CYCLE COMPLETE
    if s2_cycle_complete == 0:
        if  s2_hmi_test_type == 0:
            print("[NON-SYNC STATION 2][AUTO] Cycle completed")
            response["cycle_complete"] = True
            # Reset test type register
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)

    # TEST CHANGE
    
    if s2_cycle_complete == 1 and s2_hmi_test_type != s2_test_type:
        print(f"[AUTO][S2] Test changed → {s2_hmi_test_type}")

        write_to_hmi(HmiAddress.S2_TEST_TYPE, s2_hmi_test_type)

        response["test_changed"] = True
        response["test_id"] = s2_hmi_test_type

    return response


@csrf_exempt
def resetallstation(request, stationNum):
    try:
        s1_cycle_start_stop_status = getstatus(HmiAddress.S1_CYCLE_START_STOP_STATUS)
        s2_cycle_start_stop_status = getstatus(HmiAddress.S2_CYCLE_START_STOP_STATUS)
        
        if s1_cycle_start_stop_status == 0:
            clear_s1_livedata()
            stop_single_station1()
            write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
            return JsonResponse({"status":"success"})

        if s2_cycle_start_stop_status == 0:
            clear_s2_livedata()
            stop_single_station2()
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
            return JsonResponse({"status":"success"})
        else:
            return JsonResponse({"status":"failure",'message':'Kindly Stop the cycle to Reset'})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
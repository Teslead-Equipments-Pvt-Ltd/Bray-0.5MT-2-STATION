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

from bray_app.src import HmiAddress
from bray_app.services.single_live_page_services import( 
    clear_station_1, 
    clear_station_2, 
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

            print(s1_enabled_tst_buttons)

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
            print(s2_enabled_tst_buttons)

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
            s1_open_torque = getstatus(HmiAddress.S1_SET_OPEN_TORQUE)
            s1_close_torque = getstatus(HmiAddress. S1_SET_CLOSE_TORQUE)

        
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
                    "s1_torque_value":{
                    "open_torque": s1_open_torque,
                    "close_torque":s1_close_torque
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

            write_to_hmi(HmiAddress.S1_VALVE_CALSS, cls)
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

            s2_open_torque = getstatus(HmiAddress.S2_SET_OPEN_TORQUE)
            s2_close_torque = getstatus(HmiAddress.S2_SET_CLOSE_TORQUE)

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
                    "s2_torque_value":{
                    "open_torque": s2_open_torque,
                    "close_torque":s2_close_torque
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

                write_to_hmi(HmiAddress.S2_VALVE_CALSS, cls)
                write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, psr_unit)
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
                    write_to_hmi(HmiAddress.S1_VALVE_CALSS, int(s1_class))
                 
                    if  pressure_unit == 'psi':
                        write_to_hmi(HmiAddress.PRESSURE_UNIT, 1)

                    elif pressure_unit == 'bar':
                        write_to_hmi(HmiAddress.PRESSURE_UNIT, 2)

                    else:
                        pressure_unit == 'kg/cm2g'
                        write_to_hmi(HmiAddress.PRESSURE_UNIT, 3)

                    
                    write_to_hmi(HmiAddress. S1_TEST_TYPE, int(test_id))
                    start_station_threads(station1_enabled = True) 
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
                write_to_hmi(HmiAddress.S2_VALVE_CALSS, int(s2_class))
                
                
                if  s2_pressure_unit == 'psi':
                    write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, 1)

                elif s2_pressure_unit == 'bar':
                    write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, 2)

                else:
                    s2_pressure_unit == 'kg/cm2g'
                    write_to_hmi(HmiAddress.S2_PRESSURE_UNIT, 3)

                
                write_to_hmi(HmiAddress. S2_TEST_TYPE, int(s2_test_id))
                start_station_threads(station2_enabled = True) 
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
        "actualPressure": float(actual_pre) if actual_pre is not None else 0.0,
        "time": str(actual_time) if actual_time else "",
        "timerStatus": actual_timer_status,
        "result": result,
        "actual_duration":actual_duration,
        "actual_open_toq": actual_open_torque,
        "actual_close_toq":actual_close_torque,
        "result-value":result_value1,
        "actual_bubbles": actual_bubble,
        "actual_clamping_psr":actual_clamping_psr,
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

    return {
        "connected": True,
        "actualPressure": float(s2_actual_pre) if s2_actual_pre is not None else 0.0,
        "time": str(s2_actual_time) if s2_actual_time else "",
        "timerStatus": s2_actual_timer_status,
        "result": s2_result,
        "actual_duration": s2_actual_duration,
        "actual_open_toq": s2_actual_open_torque,
        "actual_close_toq":s2_actual_close_torque,
        "actual_bubbles": s2_actual_bubble,
        "actual_clamping_psr":s2_actual_clamping_psr,
        "result-value":result_value2
    }



station1_stop = threading.Event()
station2_stop = threading.Event()

station1_thread = None
station2_thread = None

def store_pressure_station1():
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

            
            print(f"Data stored for S1: Serial={serial_no}, Pressure={pressure}, Test_ID={s1_test_id}, Status={timer_status}")
            print("THREAD ID:", threading.get_ident())

        except Exception as e:
            print("S1 error:", e)

        time.sleep(1)


def store_pressure_station2():
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
            print(f"Data stored for S2: Serial={s2_serial_no}, Pressure={s2_pressure}, Test_ID={s2_test_id}, Status={s2_timer_status}")
            print("THREAD ID:", threading.get_ident())

        except Exception as e:
            print("S2 error:", e)

        time.sleep(1)


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
  


def stop_station1():
    global station1_thread
    if station1_thread and station1_thread.is_alive():
        station1_stop.set()
        print("Stopping Station-1 thread")

def stop_station2():
    global station2_thread
    if station2_thread and station2_thread.is_alive():
        station2_stop.set()
        print("Stopping Station-2 thread")


station1_enabled = getstatus(HmiAddress.S1_E_D_STATUS) == 1
station2_enabled = getstatus(HmiAddress.S2_E_D_STATUS) == 1

if os.environ.get("RUN_MAIN") == "true":
    # start_pressure_threads()
    start_station_threads(station1_enabled, station2_enabled)


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
        open_torque = body.get("open_torque")
        close_torque = body.get("close_torque")
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
                    open_torque,
                    close_torque,
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
                        VALVE_STATUS = %s ,
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
                    open_torque,
                    close_torque,
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
                    open_torque,
                    close_torque,
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
                    open_torque,
                    close_torque,
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


@csrf_exempt
def delete_incomplete_test(request,serialNo, stationNum):

    print("received parameters", stationNum, serialNo )

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        stationNum = int(stationNum)

        if stationNum not in [1, 2]:
            return JsonResponse({"error": "Invalid station"})

        if stationNum == 1:
            data =  delete_incomplete_test_station1(request, serialNo)

        else:
            data = delete_incomplete_test_station2(request, serialNo)

        return JsonResponse({
            "success": True,   
            "status": "",
            "station":stationNum,
            "data": data
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)




def delete_incomplete_test_station1(request, v_serial_no):  

        with transaction.atomic():
            with connection.cursor() as cursor:

                cursor.execute(f""" 
                    UPDATE master_temp_data
                    SET STATION_STATUS = %s
                    where VALVE_SER_NO = %s 
                """, ["Disabled", v_serial_no])

                cursor.execute(f"""       
                    DELETE FROM temp_testing_data_s1
                    WHERE VALVE_SERIAL_NO = %s
                    """,[v_serial_no]
                )
                cursor.execute(f"""       
                    DELETE FROM temp_pressure_analysis
                    WHERE VALVE_SER_NO = %s AND 
                    CYCLE_COMPLETE = "No"
                    """,
                    [v_serial_no]
                )
                cursor.execute(f"""       
                    DELETE FROM pressure_analysis
                    WHERE VALVE_SER_NO = %s AND
                    CYCLE_COMPLETE = "No"
                    """,
                    [v_serial_no]
                )
                cursor.execute(f"""       
                    DELETE FROM current_status_station1
                    WHERE VALVE_SERIAL_NO = %s
                    """,
                    [v_serial_no]
                )
    
        return {
        "valve_serial_no": v_serial_no,
        "station": 1,
        "station_status": "Disabled",
        "deleted": True
        }



def delete_incomplete_test_station2(request, v_serial_no):  

            with transaction.atomic():
                with connection.cursor() as cursor:

                    cursor.execute(f"""
                        UPDATE master_temp_data
                        SET STATION_STATUS = "Disabled"
                        where VALVE_SER_NO = %s 
                    """, [v_serial_no])

                    cursor.execute(f"""       
                        DELETE FROM temp_testing_data_s2
                        WHERE VALVE_SERIAL_NO = %s
                        """,
                        [v_serial_no]
                    )
                    cursor.execute(f"""       
                        DELETE FROM temp_pressure_analysis
                        WHERE VALVE_SER_NO = %s AND
                        CYCLE_COMPLETE = "No"
                        """,
                        [v_serial_no]
                    )
                    cursor.execute(f"""       
                        DELETE FROM pressure_analysis
                        WHERE VALVE_SER_NO = %s AND
                        CYCLE_COMPLETE = "No"
                        """,
                        [v_serial_no]
                    )
                    cursor.execute(f"""       
                        DELETE FROM current_status_station2
                        WHERE VALVE_SERIAL_NO = %s
                        """,
                        [v_serial_no]
                    )
    
            return {
                "valve_serial_no": v_serial_no,
                "station": 2,
                "station_status": "Disabled",
                "deleted": True
            }

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


@csrf_exempt
def cycle_complete(request, stationNum, valveSerial):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        stationNum = int(stationNum)
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

                write_to_hmi(HmiAddress.S1_E_D_STATUS, 0)
                write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
                write_to_hmi(HmiAddress.S1_HIM_TEST_TYPE, 0)
                stop_station1()
                clear_station_1()

            elif stationNum == 2:
                cursor.execute("""
                    UPDATE master_temp_data
                    SET STATION_STATUS = 'Disabled'
                    WHERE ID = 2
                """)
                cursor.execute(f"""       
                    DELETE FROM temp_testing_data_s2
                    WHERE VALVE_SERIAL_NO = %s
                    """,[valveSerial]
                )
                cursor.execute(f"""
                    DELETE FROM  temp_pressure_analysis
                    WHERE VALVE_SER_NO = %s
                """,[valveSerial]
                )
                write_to_hmi(HmiAddress.S2_E_D_STATUS, 0)
                write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
                write_to_hmi(HmiAddress.S2_HIM_TEST_TYPE, 0)
                stop_station2()
                clear_station_2()

            else:
                return JsonResponse({"error": "Invalid station number"},status=400)
            
    
         # ---------- STEP 2: ABRS PUSH (NO DB TX) ----------
        with connection.cursor() as cursor:
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
def get_current_test_id(request):
    """Get the current test_id from HMI register 2004 and return all historical pressure data"""
    try:
        test_id = TesleadSmartsyncx.read_holding_registers(2004, 1).registers[0]
        
        # Get all pressure records for this test_id
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
            "test_id": test_id,
            "pressure_history": pressure_history
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })

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
    # s1_cycle_complete   = getstatus(HmiAddress.S1_CYCLE_COMPLETE)

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
    # if s1_cycle_complete == 1:
    if  s1_hmi_test_type == 0:
        print("[AUTO][S1] Cycle completed")

        response["cycle_complete"] = True

        # Reset test type register
        write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)

        return response

    # TEST CHANGE
    # if s1_cycle_complete == 0 and s1_hmi_test_type != s1_test_type:
    if s1_hmi_test_type != s1_test_type:
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
    s2_cycle_complete   = getstatus(HmiAddress.S2_CYCLE_COMPLETE)

    response = {
        "station_enabled": True,
        "machine_mode": s2_machine_mode,
        "s1_test_id": None,
        "cycle_complete": False,
        "test_changed": False
    }

    # MANUAL MODE → do nothing
    if s2_machine_mode != 0:
        return response

    # AUTO MODE
    response["s1_test_id"] = s2_test_type

    #CYCLE COMPLETE
    if s2_cycle_complete == 1:
        print("[AUTO][S2] Cycle completed")

        response["cycle_complete"] = True

        # Reset test type register
        write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)

        return response

    # TEST CHANGE
    if s2_cycle_complete == 0 and s2_hmi_test_type != s2_test_type:
        print(f"[AUTO][S2] Test changed → {s2_hmi_test_type}")

        write_to_hmi(HmiAddress.S2_TEST_TYPE, s2_hmi_test_type)

        response["test_changed"] = True
        response["test_id"] = s2_hmi_test_type

    return response


    
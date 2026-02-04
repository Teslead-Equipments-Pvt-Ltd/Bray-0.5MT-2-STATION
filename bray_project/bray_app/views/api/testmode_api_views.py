from django.http import JsonResponse
from django.db import connection, transaction, IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bray_app.services.dashboard_testmode_service import testmode, check_cyclecomplete
from bray_app.src import HmiAddress
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx

import json


def write_to_hmi(place, value):
    """Write value to HMI register"""
    try:
        if TestleadSmartsyncx is None:
            print(f"[Error] HMI connection not established.")
            return False
        TestleadSmartsyncx.write_register(place, value)
        print(f"[HMI WRITE] Address {place} = {value}")
        return True
    except Exception as e:
        print(f"[Error writing to HMI] Address {place}: {e}")
        return False


def set_test_mode(request):
    mode = request.GET.get('mode', 'manual')
    testmode(mode)
    return JsonResponse({"status": "success", "mode": mode})


# api
def check_incompletetest(request):
    data = check_cyclecomplete()
    print("incompelte data",  data)

    return JsonResponse({
        "found": bool(data),
        "tests": data,
        "no_of_stations": len(data)
    })




@csrf_exempt
def delete_incomplete_test(request, serialNo, stationNum):

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

                cursor.execute(""" TRUNCATE temp_testing_data_s1 """)

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

                cursor.execute(""" TRUNCATE current_status_station1 """)
        
        # Reset HMI addresses for Station 1 (same as cycle_complete)
        print(f"[DELETE_TEST] Resetting HMI addresses for Station 1")
        write_to_hmi(HmiAddress.S1_TEST_TYPE, 0)
        write_to_hmi(HmiAddress.S1_VALVE_SIZE, 0)
        write_to_hmi(HmiAddress.S1_VALVE_CLASS, 0)
        write_to_hmi(HmiAddress.S1_SET_PRESSURE, 0)
        write_to_hmi(HmiAddress.S1_SET_HOLDING_TIME, 0)
        write_to_hmi(HmiAddress.S1_E_D_STATUS, 0)
    
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

                    # cursor.execute(f"""       
                    #     DELETE FROM temp_testing_data_s2
                    #     WHERE VALVE_SERIAL_NO = %s
                    #     """,
                    #     [v_serial_no]
                    # )

                    cursor.execute(""" TRUNCATE temp_testing_data_s2 """)

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
                    # cursor.execute(f"""       
                    #     DELETE FROM current_status_station2
                    #     WHERE VALVE_SERIAL_NO = %s
                    #     """,
                    #     [v_serial_no]
                    # )
                    cursor.execute(""" TRUNCATE current_status_station2 """)
            
            # Reset HMI addresses for Station 2 (same as cycle_complete)
            print(f"[DELETE_TEST] Resetting HMI addresses for Station 2")
            write_to_hmi(HmiAddress.S2_TEST_TYPE, 0)
            write_to_hmi(HmiAddress.S2_VALVE_SIZE, 0)
            write_to_hmi(HmiAddress.S2_VALVE_CLASS, 0)
            write_to_hmi(HmiAddress.S2_SET_PRESSURE, 0)
            write_to_hmi(HmiAddress.S2_SET_HOLDING_TIME, 0)
            write_to_hmi(HmiAddress.S2_E_D_STATUS, 0)
    
            return {
                "valve_serial_no": v_serial_no,
                "station": 2,
                "station_status": "Disabled",
                "deleted": True
            }


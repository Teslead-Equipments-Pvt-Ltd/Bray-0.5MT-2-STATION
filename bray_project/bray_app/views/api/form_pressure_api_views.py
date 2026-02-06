from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bray_app.decorators import permission_required
import json
from bray_app.services.form_service import get_testname
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx
from bray_app.src import HmiAddress
    
    
@csrf_exempt
@permission_required("form")
def get_pressure_duration(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            standard = data.get("standard")
            valve_size = data.get("size")
            valve_class = data.get("class")
            valve_type = data.get("type")
            shell_material = data.get("body_material")
            pressure_unit = data.get("pressure_unit")
            station = data.get("station")
            
            test_name, pressure, duration, test_ids, degree = get_testname(
                standard, valve_size, valve_type, shell_material, valve_class
            )
            
            if pressure_unit.lower() == "psi":
                pressure = [float(p) * 14.5 for p in pressure]  # ← unchanged
                invalid = [p for p in pressure if p is None]

                if invalid:
                    raise ValueError("Pressure contains NULL values. Check test configuration.")

            pressure_duration = {
                "test_name": test_name,
                "pressure": pressure,
                "duration": duration,
                "testid": test_ids,
                "degree": degree
            }
            return JsonResponse({"pressure_duration": pressure_duration})

    except TypeError as e:
        return JsonResponse({
            "error": "Invalid pressure value (NULL found).",
            "details": str(e)
        }, status=400)

    except ValueError as e:
        return JsonResponse({
            "error": str(e)
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "error": "Unexpected server error",
            "details": str(e)
        }, status=500)


# def get_syncstatus(request):
#     try:
#         response = TestleadSmartsyncx.read_holding_registers(HmiAddress.SYNC_OR_NON_SYNC_MODE, 1)
#         if hasattr(response, 'registers'):
#             sync_status = response.registers[0]
#         else:
#             # Handle error (e.g., connection failed)
#             print(f"Modbus Read Error: {response}")
#             sync_status = 0
#     except Exception as e:
#         print(f"Modbus Exception: {e}")
#         sync_status = 0
        
#     return JsonResponse({"status": "success", "syncstatus": sync_status})


@csrf_exempt
@permission_required("form")
def validate_psr_unit(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            station_id = data.get("station_id")
            psr_unit = data.get("psr_unit")
            
            # Map station string to ID if necessary, or ensure frontend sends ID (1/2)
            # Assuming station_id is passed as integer or convertible string
            
            if not station_id or not psr_unit:
                 return JsonResponse({"valid": True}) # Or error if strict

            from django.db import connection
            with connection.cursor() as cursor:
                # Check for other enabled stations
                # We want to find ANY record where STATION_STATUS is 'Enabled' AND ID is NOT the current one
                cursor.execute("""
                    SELECT PRESSURE_UNIT FROM master_temp_data 
                    WHERE STATION_STATUS = 'Enabled' AND ID != %s
                """, [station_id])
                result = cursor.fetchone()
                
                if result:
                    existing_unit = result[0]
                    # Compare units (case-insensitive perhaps?)
                    if existing_unit and existing_unit.strip().lower() != psr_unit.strip().lower():
                         return JsonResponse({
                            "valid": False,
                            "existing_unit": existing_unit,
                            "error": f"Validation Failed: Another station is running with Pressure Unit '{existing_unit}'. You selected '{psr_unit}'."
                        })
            
            return JsonResponse({"valid": True})

    except Exception as e:
        return JsonResponse({
            "error": "Validation error",
            "details": str(e)
        }, status=500)
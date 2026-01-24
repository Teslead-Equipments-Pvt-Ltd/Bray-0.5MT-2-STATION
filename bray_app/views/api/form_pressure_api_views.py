from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bray_app.decorators import permission_required
import json
from bray_app.services.form_service import get_testname
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx
    
# @csrf_exempt
# @permission_required("form")
# def get_pressure_duration(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         standard = data.get("standard")
#         valve_size = data.get("size")
#         valve_class = data.get("class")
#         valve_type = data.get("type")
#         shell_material = data.get("body_material")
#         pressure_unit = data.get("pressure_unit")
#         station = data.get("station")
        
#         test_name, pressure, duration,test_ids,degree = get_testname(
#             standard, valve_size, valve_type, shell_material, valve_class
#         )
        
#         if pressure_unit.lower() == "psi":
#             pressure = [float(p) * 14.5 for p in pressure]
            
#         pressure_duration = {
#             "test_name": test_name,
#             "pressure": pressure,
#             "duration": duration,
#             "testid":test_ids,
#             "degree":degree
#         }
#         return JsonResponse({"pressure_duration": pressure_duration})
    


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


def get_syncstatus(request):
    try:
        response = TestleadSmartsyncx.read_holding_registers(2018, 1)
        if hasattr(response, 'registers'):
            sync_status = response.registers[0]
        else:
            # Handle error (e.g., connection failed)
            print(f"Modbus Read Error: {response}")
            sync_status = 0
    except Exception as e:
        print(f"Modbus Exception: {e}")
        sync_status = 0
        
    return JsonResponse({"status": "success", "syncstatus": sync_status})
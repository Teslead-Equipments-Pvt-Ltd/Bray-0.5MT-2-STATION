from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bray_app.decorators import permission_required
from bray_app.services.dashboard_newtest_service import check_cyclecomplete

import json


# def check_incompletetest(request):
#     cycle_status, serial_no = check_cyclecomplete()
#     print("values cycle status", cycle_status)

#     if cycle_status:
#         cycle_status = "Incomplete Test Found"
#     else:
#         cycle_status = "No Incomplete Test"
#     return JsonResponse({"cycle_status": cycle_status, "serial_no": serial_no})

# api
def check_incompletetest(request):
    data = check_cyclecomplete()
    print("incompelte data",  data)

    return JsonResponse({
        "found": bool(data),
        "tests": data,
        "no_of_stations": len(data)
    })






# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt


# @csrf_exempt
# def check_incompletetest(request):

#     if request.method != "GET":
#         return JsonResponse({"error": "Invalid method"}, status=405)

#     try:
#         station1, station2 = check_cyclecomplete()

#         return JsonResponse({
#             "status": "success",
#             "station1": {
#                 "exists": bool(station1),
#                 "data": {
#                     "id": station1[0],
#                     "valve_serial_no": station1[1],
#                     "station_status": station1[2],
#                     "cycle_complete": station1[3],
#                 } if station1 else None
#             },
#             "station2": {
#                 "exists": bool(station2),
#                 "data": {
#                     "id": station2[0],
#                     "valve_serial_no": station2[1],
#                     "station_status": station2[2],
#                     "cycle_complete": station2[3],
#                 } if station2 else None
#             }
#         })

#     except Exception as e:
#         return JsonResponse({
#             "status": "error",
#             "message": str(e)
#         }, status=500)

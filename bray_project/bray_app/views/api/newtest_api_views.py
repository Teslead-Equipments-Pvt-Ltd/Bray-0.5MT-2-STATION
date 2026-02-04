from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bray_app.decorators import permission_required
from bray_app.services.dashboard_newtest_service import check_cyclecomplete
import json



# api
def check_incompletetest(request):
    data = check_cyclecomplete()
    print("incompelte data",  data)

    return JsonResponse({
        "found": bool(data),
        "tests": data,
        "no_of_stations": len(data)
    })




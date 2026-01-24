from django.http import JsonResponse
from bray_app.services.dashboard_testmode_service import testmode


def set_test_mode(request):
    mode = request.GET.get('mode', 'manual')
    testmode(mode)
    return JsonResponse({"status": "success", "mode": mode})

from django.http import JsonResponse

from bray_app.services.form_service import clear_station1,clear_station2

def clear_station1_form(request):
    clear_station1()
    return JsonResponse({"status":"success"})


def clear_station2_form(request):
    clear_station2()
    return JsonResponse({"status":"success"})
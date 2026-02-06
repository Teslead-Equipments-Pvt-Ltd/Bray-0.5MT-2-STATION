from django.http import JsonResponse

from bray_app.services.form_service import cancel_station1,cancel_station2

def cancel_station1_form(request):
    cancel_station1()
    return JsonResponse({"status":"success"})

def cancel_station2_form(request):
    cancel_station2()
    return JsonResponse({"status":"success"})
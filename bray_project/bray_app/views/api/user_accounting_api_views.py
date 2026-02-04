from django.http import JsonResponse
from bray_app.decorators import login_required
from bray_app.services.user_accounting_service import get_all_user_accounting


@login_required
def get_all_user_accounting_api(request):
    """GET endpoint to retrieve all user accounting records."""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    try:
        employees = get_all_user_accounting()
        return JsonResponse({
            "employees": employees,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

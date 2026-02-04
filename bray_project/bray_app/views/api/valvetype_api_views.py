from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bray_app.decorators import permission_required
from bray_app.services.valvetype_service import (
    add_valve_type,
    edit_valve_type,
    delete_valve_type,
    get_all_valve_types,
    delete_multiple_valve_types,
)
import json


@permission_required("Valve Type")
@require_http_methods(["GET"])
def get_all_valve_types_api(request):
    """
    GET endpoint to retrieve all valve types with their associated test types.
    Returns JSON similar in spirit to the standards list API so the frontend
    can build the table and forms purely via JavaScript.
    """
    try:
        data = get_all_valve_types()
        return JsonResponse(
            {
                "valve_types": data.get("valve_types", []),
                "test_types": data.get("test_types", []),
                "existing_codes": data.get("existing_codes", []),
                "existing_names": data.get("existing_names", []),
            }
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"An error occurred: {str(e)}"}, status=500
        )


@permission_required("Valve Type")
@require_http_methods(["POST"])
@csrf_exempt
def valve_type_add_api(request):
    """API endpoint for adding valve type"""
    try:
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        test_types = data.get("test_types", [])

        # Validation
        if not name:
            return JsonResponse(
                {"success": False, "error": "Valve Type Name cannot be empty."}
            )

        if not test_types:
            return JsonResponse(
                {"success": False, "error": "Please select at least one test type."}
            )

        # Add valve type
        result = add_valve_type(name, description, test_types)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON data."})
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"An error occurred: {str(e)}"}
        )


@permission_required("Valve Type")
@require_http_methods(["POST"])
@csrf_exempt
def valve_type_edit_api(request, valve_type_id):
    """API endpoint for editing valve type"""
    try:
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        test_types = data.get("test_types", [])

        # Validation
        if not name:
            return JsonResponse(
                {"success": False, "error": "Valve Type Name cannot be empty."}
            )

        if not test_types:
            return JsonResponse(
                {"success": False, "error": "Please select at least one test type."}
            )

        # Edit valve type
        result = edit_valve_type(valve_type_id, name, description, test_types)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON data."})
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"An error occurred: {str(e)}"}
        )


@permission_required("Valve Type")
@require_http_methods(["POST"])
@csrf_exempt
def valve_type_delete_api(request, valve_type_id):
    """API endpoint for deleting valve type"""
    try:
        result = delete_valve_type(valve_type_id)
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"An error occurred: {str(e)}"}
        )


@permission_required("Valve Type")
@require_http_methods(["POST"])
@csrf_exempt
def bulk_delete_valvetype_api(request):
    """API endpoint for bulk deleting valve types"""
    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if not ids:
            return JsonResponse({"error": "No IDs provided"})

        deleted_count = delete_multiple_valve_types(ids)

        return JsonResponse({
            "success": True, 
            "deleted_count": deleted_count, 
            "message": "Valve Types deleted successfully"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

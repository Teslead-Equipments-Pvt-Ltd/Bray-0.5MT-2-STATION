from django.http import JsonResponse
from bray_app.decorators import permission_required
from bray_app.services.valve_class_service import (
    get_all_valve_classes,
    get_next_class_id,
    insert_valve_class,
    update_valve_class,
    delete_valve_class_record,
    check_duplicate_name,
    delete_multiple_valve_classes
)
import json


@permission_required("Valve Class")
def get_all_valve_classes_api(request):
    """
    GET endpoint to retrieve all valve classes.
    Returns JSON array of valve classes.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    valve_classes = get_all_valve_classes()
    
    # Convert tuple rows to dictionaries for JSON serialization
    valve_classes_list = []
    for row in valve_classes:
        valve_classes_list.append({
            "id": row[0],           # ID
            "class_id": row[1],     # CLASS_ID
            "name": row[2],         # CLASS_NAME
            "description": row[3],  # CLASS_DESC
        })
    
    # Also return existing names for duplicate validation
    existing_names = [row[2] for row in valve_classes]
    
    # Get superuser level from session
    superuser_level = request.session.get("superuser", 0)
    
    return JsonResponse({
        "valve_classes": valve_classes_list,
        "existing_names": existing_names,
        "superuser_level": superuser_level,
        "message": "Valve Classes retrieved successfully",
        "success": True,
    })


@permission_required("Valve Class")
def add_valve_class_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    name = request.POST.get("name", "").strip()
    desc = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse({"success": False, "error": "Name required"}, status=400)

    if check_duplicate_name(name):
        return JsonResponse({"success": False, "error": "Name already exists"}, status=400)

    next_id = get_next_class_id()
    insert_valve_class(next_id, name, desc)

    return JsonResponse({"success": True, "message": "Valve Class added", "id": next_id})


@permission_required("Valve Class")
def edit_valve_class_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    name = request.POST.get("name", "").strip()
    desc = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse({"success": False, "error": "Name required"}, status=400)

    if check_duplicate_name(name, pk):
        return JsonResponse({"success": False, "error": "Duplicate name"}, status=400)

    update_valve_class(pk, name, desc)

    return JsonResponse({"success": True, "message": "Valve Class updated"})


@permission_required("Valve Class")
def delete_valve_class_api(request, pk):
    delete_valve_class_record(pk)
    return JsonResponse({"success": True, "message": "Valve Class deleted successfully"})


@permission_required("Valve Class")
def bulk_delete_valve_classes_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if not ids:
            return JsonResponse({"error": "No IDs provided"})

        deleted_count = delete_multiple_valve_classes(ids)

        return JsonResponse({"success": True, "deleted_count": deleted_count, "message": "Valve Classes deleted successfully"})
    except Exception as e:
        return JsonResponse({"success": False,"error": str(e)}, status=500)


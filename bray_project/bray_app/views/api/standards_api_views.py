from django.http import JsonResponse
from bray_app.decorators import permission_required
from bray_app.services.standards_service import (
    get_all_standards,
    get_next_standard_id,
    insert_standard,
    update_standard,
    delete_standard_record,
    check_duplicate_name,
    delete_multiple_standard_records
)
import json


@permission_required("Standard")
def get_all_standards_api(request):
    """
    GET endpoint to retrieve all standards.
    Returns JSON array of standards.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    standards = get_all_standards()
    
    # Convert tuple rows to dictionaries for JSON serialization
    standards_list = []
    for row in standards:
        standards_list.append({
            "id": row[0],           # ID
            "standard_id": row[1],  # STANDARD_ID
            "name": row[2],         # STANDARD_NAME
            "description": row[3],  # STANDARD_DESC
            "created_date": str(row[4]) if row[4] else None,  # CREATED_DATE
            "updated_date": str(row[5]) if row[5] else None,  # UPDATED_DATE
        })
    
    # Also return existing names for duplicate validation
    existing_names = [row[2] for row in standards]
    
    return JsonResponse({
        "standards": standards_list,
        "existing_names": existing_names
    })


@permission_required("Standard")
def add_standard_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    name = request.POST.get("name", "").strip()
    desc = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse({"error": "Name required"}, status=400)

    if check_duplicate_name(name):
        return JsonResponse({"error": "Name already exists"}, status=400)

    next_id = get_next_standard_id()
    
    insert_standard(next_id, name, desc)

    return JsonResponse({"message": "Standard added", "id": next_id})


@permission_required("Standard")
def edit_standard_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    name = request.POST.get("name", "").strip()
    desc = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse({"error": "Name required"}, status=400)

    if check_duplicate_name(name, pk):
        return JsonResponse({"error": "Name already exists"}, status=400)

    update_standard(pk, name, desc)

    return JsonResponse({"message": "Standard updated"})


@permission_required("Standard")
def delete_standard_api(request, pk):
    delete_standard_record(pk)
    return JsonResponse({"success": True, "message": "Standard deleted successfully"})

@permission_required("Standard")
def bulk_delete_standards_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if not ids:
            return JsonResponse({"error": "No IDs provided"})

        deleted_count = delete_multiple_standard_records(ids)

        return JsonResponse({"success": True, "deleted_count": deleted_count, "message": "Standards deleted successfully"})
    except Exception as e:
        return JsonResponse({"success": False,"error": str(e)}, status=500)
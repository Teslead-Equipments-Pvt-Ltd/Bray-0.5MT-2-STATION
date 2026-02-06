from django.http import JsonResponse
from bray_app.decorators import permission_required
from bray_app.services.instrument_type_service import (
    get_all_instrument_types,
    get_next_instrument_type_id,
    insert_instrument_type,
    update_instrument_type,
    delete_instrument_type_record,
    check_duplicate_name
)


@permission_required("Instrument Type")
def get_all_instrument_types_api(request):
    """GET endpoint to retrieve all instrument types."""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    rows = get_all_instrument_types()
    
    instrument_types_list = []
    for row in rows:
        instrument_types_list.append({
            "id": row[0],
            "instrument_name": row[1],
            "status": row[2],
        })
    
    existing_names = [row[1] for row in rows]
    
    # Get superuser level from session
    superuser_level = request.session.get("superuser", 0)
    
    return JsonResponse({
        "instrument_types": instrument_types_list,
        "existing_names": existing_names,
        "superuser_level": superuser_level
    })


@permission_required("Instrument Type")
def save_instrument_types_api(request):
    """API to save all instrument type rows (bulk save)"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        instrument_ids = request.POST.getlist("instrument_id[]")
        instrument_names = request.POST.getlist("instrument_name[]")
        statuses = request.POST.getlist("status[]")

        # Check if there's at least one valid row with data
        valid_rows = [name.strip() for name in instrument_names if name.strip()]
        if not valid_rows:
            return JsonResponse({"error": "Please enter at least one instrument name"}, status=400)

        # Validate duplicate names within form
        name_map = {}
        for i, name in enumerate(instrument_names):
            name = name.strip()
            if not name:
                continue
            if name.lower() in name_map:
                return JsonResponse({"error": f'Duplicate instrument name "{name}" in form'}, status=400)
            name_map[name.lower()] = i

        # Process each record
        for instrument_id, instrument_name, status in zip(instrument_ids, instrument_names, statuses):
            instrument_name = instrument_name.strip()
            status = status.strip()
            
            # Skip empty rows
            if not instrument_name:
                continue
            
            if instrument_id and instrument_id.strip():
                # Update existing record
                update_instrument_type(instrument_id, instrument_name, status)
            else:
                # Insert new record
                next_id = get_next_instrument_type_id()
                insert_instrument_type(next_id, instrument_name, status)

        return JsonResponse({"success": True, "message": "Instrument types saved successfully"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@permission_required("Instrument Type")
def delete_instrument_type_api(request, pk):
    """API to delete instrument type"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
    
    try:
        delete_instrument_type_record(pk)
        return JsonResponse({"success": True, "message": "Instrument type deleted successfully"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from bray_app.decorators import permission_required
from bray_app.services.testtype_service import (
    getall_testtype,
    get_enabled_categories,
    check_duplicate_testname,
    get_columnnames,
    update_testtype
)
from django.db import connection
import json


@permission_required("Test Type")
@require_http_methods(["GET"])
def get_all_testtypes_api(request):
    """
    GET endpoint to retrieve all test types plus supporting data.
    """
    try:
        test_types = getall_testtype()
        category_list = get_enabled_categories()

        # Make sure "NONE" exists as first option (matching page view)
        if "NONE" not in category_list:
            category_list.insert(0, "NONE")

        testtype_list = []
        for row in test_types:
            testtype_list.append(
                {
                    "test_id": row[0],
                    "test_name": row[1],
                    "medium": row[2],
                    "category": row[3],
                    "status": row[4],
                }
            )

        existing_names = [row[1] for row in test_types]

        return JsonResponse(
            {
                "testtypes": testtype_list,
                "categories": category_list,
                "existing_names": existing_names,
            }
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while fetching test types: {str(e)}"},
            status=500,
        )


@permission_required("Test Type")
@require_http_methods(["POST"])
@csrf_exempt
def update_testtypes_api(request):
    """
    POST endpoint to bulk-update test types.
    Body JSON format:
    {
        "items": [
            {
                "test_id": ...,
                "test_name": "...",
                "medium": "...",
                "category": "...",
                "status": "ENABLE" | "DISABLE"
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data."}, status=400)

    items = data.get("items", [])

    if not isinstance(items, list) or not items:
        return JsonResponse({"error": "No test types provided."}, status=400)

    # ----- Validation: empty & duplicate names in payload -----
    seen_names = set()

    for idx, item in enumerate(items, start=1):
        name = (item.get("test_name") or "").strip()
        if not name:
            return JsonResponse(
                {"error": f"Test name cannot be empty at row {idx}."}, status=400
            )

        name_lower = name.lower()
        if name_lower in seen_names:
            return JsonResponse(
                {
                    "error": f'Duplicate test name "{name}" found in payload. Please use unique names.'
                },
                status=400,
            )
        seen_names.add(name_lower)

    # Process and update each item (check DB duplicates per item)
    try:
        for idx, item in enumerate(items, start=1):
            # Validate and normalise fields for this item
            try:
                test_id = int(item.get("test_id"))
            except (TypeError, ValueError):
                return JsonResponse(
                    {"error": f"Invalid or missing test_id at row {idx}."},
                    status=400,
                )

            testname = (item.get("test_name") or "").strip()
            medium = (item.get("medium") or "").strip()
            category = (item.get("category") or "").strip()
            status = (item.get("status") or "").strip()

            testname_lower = testname.lower()

            # Check duplicate against DB for this item
            duplicate = check_duplicate_testname(testname_lower, test_id)
            if duplicate:
                duplicate_id, duplicate_name = duplicate
                return JsonResponse(
                    {
                        "error": f'Test name "{testname}" already exists (found as "{duplicate_name}"). Please use a unique name.'
                    },
                    status=400,
                )

            # Determine pressure/duration columns if category provided
            pressure_column = None
            duration_column = None
            if category and category != "NONE":
                row = get_columnnames(category)
                if row:
                    pressure_column, duration_column = row

            # Perform update for this item
            update_testtype(testname, medium, category, status, pressure_column, duration_column, test_id)

        return JsonResponse({"message": "Test Type details updated successfully!"})
    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while updating test types: {str(e)}"},
            status=500,
        )



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bray_app.services.shell_material_service import (
    get_all_materials, get_material_detail, get_enabled_categories,
    get_pressure_data, get_next_shell_material_id,
    save_shell_material, delete_shell_material,
    get_all_classes, delete_multiple_shell_materials
)

from django.db import connection


def shell_meta_api(request):
    """GET metadata for shell material page"""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    classes = get_all_classes()
    categories = get_enabled_categories()

    
    # Get existing names for duplicate validation
    with connection.cursor() as cursor:
        cursor.execute("SELECT SHELL_MATERIAL_NAME FROM shell_material WHERE SHELL_MATERIAL_NAME IS NOT NULL")
        existing_names = [row[0] for row in cursor.fetchall()]
    
    superuser_level = request.session.get('superuser', 0)

    return JsonResponse({
        "classes": [{"id": c[0], "name": c[1]} for c in classes],
        "categories": [{"name": c[0], "col": c[1]} for c in categories],
        "existing_names": existing_names,
        "all_categories_disabled": len(categories) == 0,
        "superuser_level": superuser_level
    })


def shell_get_all_api(request):
    """GET all shell materials"""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    materials = get_all_materials()
    materials_list = []
    for row in materials:
        materials_list.append({
            "id": row[0],
            "shell_id": row[1],
            "name": row[2],
            "description": row[3] or ""
        })
    
    return JsonResponse({"materials": materials_list})


def shell_get_one_api(request, material_id):
    """GET single shell material for editing"""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    row = get_material_detail(material_id)
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    
    categories = get_enabled_categories()
    pressure_data = get_pressure_data(row[1], categories)
    
    pressure_list = []
    for d in pressure_data:
        entry = {"id": d[0], "class_id": d[1]}
        for i, (_, col) in enumerate(categories):
            entry[col] = d[i + 2]
        pressure_list.append(entry)
    
    return JsonResponse({
        "id": row[0],
        "shell_id": row[1],
        "name": row[2],
        "description": row[3] or "",
        "pressure_data": pressure_list
    })


@csrf_exempt
def shell_add_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    import json
    try:
        if request.content_type == "application/json":
            body = json.loads(request.body)
            name = body.get("name", "").strip()
            desc = body.get("description", "").strip()
            rows = body.get("rows", [])
        else:
            name = request.POST.get("name", "").strip()
            desc = request.POST.get("description", "").strip()
            rows = []
            # Parse rows from form data
            class_ids = request.POST.getlist("Class[]")
            categories = get_enabled_categories()
            for i, class_id in enumerate(class_ids):
                row = {"class_id": int(class_id)}
                for _, col_name in categories:
                    val = request.POST.getlist(f"{col_name}[]")[i] if i < len(request.POST.getlist(f"{col_name}[]")) else ""
                    row[col_name] = val
                rows.append(row)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    if not name:
        return JsonResponse({"error": "Name required"}, status=400)

    categories = get_enabled_categories()
    if not categories:
        return JsonResponse({"error": "No enabled categories"}, status=400)

    # Generate next shell material ID for new records
    shell_id = get_next_shell_material_id()

    data = {
        "material_id": None,
        "shell_id": shell_id,
        "name": name,
        "desc": desc,
        "rows": rows
    }

    try:
        save_shell_material(data, categories)
        return JsonResponse({"success": True, "message": "Shell material added"})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An error occurred while saving the material"}, status=500)
    


@csrf_exempt
def shell_edit_api(request, material_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    row = get_material_detail(material_id)
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)

    shell_code = row[1]
    categories = get_enabled_categories()

    import json
    try:
        if request.content_type == "application/json":
            body = json.loads(request.body)
            name = body.get("name", "").strip()
            desc = body.get("description", "").strip()
            rows = body.get("rows", [])
        else:
            name = request.POST.get("name", "").strip()
            desc = request.POST.get("description", "").strip()
            rows = []
            # Parse rows from form data
            class_ids = request.POST.getlist("Class[]")
            for i, class_id in enumerate(class_ids):
                row = {"class_id": int(class_id)}
                for _, col_name in categories:
                    val = request.POST.getlist(f"{col_name}[]")[i] if i < len(request.POST.getlist(f"{col_name}[]")) else ""
                    row[col_name] = val
                rows.append(row)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    if not name:
        return JsonResponse({"error": "Name required"}, status=400)

    data = {
        "material_id": material_id,
        "shell_id": shell_code,
        "name": name,
        "desc": desc,
        "rows": rows
    }

    try:
        save_shell_material(data, categories)
        return JsonResponse({"success": True, "message": "Shell material updated"})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An error occurred while updating the material"}, status=500)


def shell_delete_api(request, shell_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    try:
        delete_shell_material(shell_id)
        return JsonResponse({"success": True, "message": "Shell material deleted"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def bulk_delete_shell_materials_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    import json
    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if not ids:
            return JsonResponse({"error": "No IDs provided"})

        deleted_count = delete_multiple_shell_materials(ids)

        return JsonResponse({"success": True, "deleted_count": deleted_count, "message": "Shell materials deleted successfully"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


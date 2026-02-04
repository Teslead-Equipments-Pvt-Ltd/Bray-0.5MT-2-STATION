from django.http import JsonResponse
from bray_app.decorators import login_required
from bray_app.services.employee_service import (
    get_all_employees,
    get_employee_by_id,
    get_employee_permissions,
    get_existing_employee_codes,
    get_menu_items_by_section,
    check_duplicate_code,
    insert_employee,
    update_employee,
    delete_employee,
    delete_multiple_employees,
    update_employee_permissions,
)
import json
import re


def validate_employee_name(name):
    """Validate employee name according to business rules."""
    if not name or not name.strip():
        return "Employee name is required"
    
    name = name.strip()
    
    # Must start with a letter
    if not re.match(r'^[a-zA-Z]', name):
        return "Name must start with a letter"
    
    # Must be alphanumeric only
    if not re.match(r'^[a-zA-Z0-9]+$', name):
        return "Name must contain only letters and numbers"
    
    # Cannot be all numbers (redundant check but keeping for clarity)
    if re.match(r'^\d+$', name):
        return "Name cannot be all numbers"
    
    return None  # Valid


@login_required
def get_all_employees_api(request):
    """GET endpoint to retrieve all employees with permissions."""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    employees = get_all_employees()
    employee_ids = [emp['id'] for emp in employees]
    permissions_map = get_employee_permissions(employee_ids)
    
    for emp in employees:
        emp['permissions'] = permissions_map.get(emp['id'], [])
        # Don't send password to frontend
        emp.pop('password', None)
    
    existing_codes = get_existing_employee_codes()
    menu_items_by_section = get_menu_items_by_section()
    
    return JsonResponse({
        "employees": employees,
        "existing_codes": existing_codes,
        "menu_items_by_section": menu_items_by_section,
    })


@login_required
def get_employee_api(request, pk):
    """GET endpoint to retrieve a single employee."""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    employee = get_employee_by_id(pk)
    if not employee:
        return JsonResponse({"error": "Employee not found"}, status=404)
    
    permissions_map = get_employee_permissions([pk])
    employee['permissions'] = permissions_map.get(pk, [])
    employee.pop('password', None)
    
    return JsonResponse({"employee": employee})


@login_required
def add_employee_api(request):
    """POST endpoint to add a new employee."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    employee_type = request.POST.get('employee_type', '').strip()
    code = request.POST.get('employee_code', '').strip()
    name = request.POST.get('employee_name', '').strip()
    password = request.POST.get('password', '').strip()
    email = request.POST.get('email', '').strip()
    mobile = request.POST.get('mobile', '').strip()
    status = request.POST.get('status', 'active').strip()
    image = request.FILES.get('image')
    selected_permissions = request.POST.getlist('menu_items')
    
    if not code:
        return JsonResponse({"error": "Employee code is required"}, status=400)
    
    if not name:
        return JsonResponse({"error": "Employee name is required"}, status=400)
    
    # Validate employee name
    name_error = validate_employee_name(name)
    if name_error:
        return JsonResponse({"error": name_error}, status=400)
    
    if not password:
        return JsonResponse({"error": "Password is required"}, status=400)
    
    if check_duplicate_code(code):
        return JsonResponse({"error": "Employee code already exists"}, status=400)
    
    image_name = image.name if image else None
    new_id = insert_employee(employee_type, code, name, password, email, mobile, image_name, status)
    
    if new_id and selected_permissions:
        update_employee_permissions(new_id, selected_permissions)
    
    return JsonResponse({
        "success": True,
        "message": "Employee added successfully",
        "id": new_id
    })


@login_required
def edit_employee_api(request, pk):
    """POST endpoint to update an employee."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    employee_type = request.POST.get('employee_type', '').strip()
    code = request.POST.get('employee_code', '').strip()
    name = request.POST.get('employee_name', '').strip()
    password = request.POST.get('password', '').strip()  # Optional - only update if provided
    email = request.POST.get('email', '').strip()
    mobile = request.POST.get('mobile', '').strip()
    status = request.POST.get('status', 'active').strip()
    image = request.FILES.get('image')
    selected_permissions = request.POST.getlist('menu_items')
    
    if not code:
        return JsonResponse({"error": "Employee code is required"}, status=400)
    
    if not name:
        return JsonResponse({"error": "Employee name is required"}, status=400)
    
    # Validate employee name
    name_error = validate_employee_name(name)
    if name_error:
        return JsonResponse({"error": name_error}, status=400)
    
    if check_duplicate_code(code, exclude_id=pk):
        return JsonResponse({"error": "Employee code already exists"}, status=400)
    
    image_name = image.name if image else None
    # Password is optional for edit - pass empty string if not provided (won't update)
    update_employee(pk, employee_type, code, name, password, email, mobile, status, image_name)
    update_employee_permissions(pk, selected_permissions)
    
    return JsonResponse({
        "success": True,
        "message": "Employee updated successfully"
    })


@login_required
def delete_employee_api(request, pk):
    """POST/DELETE endpoint to delete an employee."""
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    delete_employee(pk)
    
    return JsonResponse({
        "success": True,
        "message": "Employee deleted successfully"
    })


@login_required
def bulk_delete_employees_api(request):
    """POST endpoint to delete multiple employees."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])
        
        if not ids:
            return JsonResponse({"error": "No IDs provided"}, status=400)
        
        deleted_count = delete_multiple_employees(ids)
        
        return JsonResponse({
            "success": True,
            "deleted_count": deleted_count,
            "message": "Employees deleted successfully"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

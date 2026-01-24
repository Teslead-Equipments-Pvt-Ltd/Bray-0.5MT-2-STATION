from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse
from django.db import connection
from django.contrib import messages

def login_required(view_func):
    """
    Decorator to check if user is logged in (has session with username).
    Redirects to login page if not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        username = request.session.get('username')
        print(f"[LOGIN_REQUIRED] Checking session for {view_func.__name__}")
        print(f"[LOGIN_REQUIRED] Session keys: {list(request.session.keys())}")
        print(f"[LOGIN_REQUIRED] Username: {username}")
        
        if not username:
            print(f"[LOGIN_REQUIRED] No username found, redirecting to login")
            # If it's an AJAX request, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': 'Session expired. Please log in again.'}, status=401)
            # Otherwise redirect to login
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        print(f"[LOGIN_REQUIRED] User {username} authenticated, proceeding")
        return view_func(request, *args, **kwargs)
    return wrapper


def permission_required(menu_item_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            username = request.session.get('username')
            superuser_level = request.session.get('superuser')
            
            # First check if user is logged in
            if not username:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'message': 'Session expired. Please log in again.'}, status=401)
                messages.error(request, 'Please log in to access this page.')
                return redirect('login')
            
            # Convert superuser_level to int for comparison
            try:
                if superuser_level is None:
                    superuser_level = 0
                else:
                    superuser_level = int(superuser_level)
            except (ValueError, TypeError):
                superuser_level = 0
            
            # Superuser level 2: Can access everything
            if superuser_level == 2:
                return view_func(request, *args, **kwargs)
            
            # Superuser level 1: Can access everything except "Category", "Test Type", "Instrument Type", "CategoryInstrument", and "TypeTest"
            if superuser_level == 1:
                if menu_item_name in ["Category", "Test Type", "Instrument Type", "CategoryInstrument", "TypeTest"]:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                        return JsonResponse({'status': 'error', 'message': 'You do not have permission to access this page.'}, status=403)
                    messages.error(request, 'You do not have permission to access this page.')
                    return redirect('dashboard')
                return view_func(request, *args, **kwargs)
            
            # Superuser level 0: Check menu permissions
            try:
                with connection.cursor() as cursor:
                    # Get employee ID from employee table (not newapp_employee)
                    cursor.execute("SELECT id FROM employee WHERE name = %s", [username])
                    row = cursor.fetchone()
                    
                    if not row:
                        print(f"[PERMISSION] User not found in employee table: {username}")
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                            return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=403)
                        messages.error(request, 'User not found.')
                        return redirect('login')
                    
                    employee_id = row[0]
                    
                    # First check if user has ANY permissions configured
                    cursor.execute("""
                        SELECT COUNT(*) FROM newapp_usermenupermission WHERE employee_id = %s
                    """, [employee_id])
                    total_permissions = cursor.fetchone()[0]
                    
                    # If no permissions configured at all, allow access to everything
                    if total_permissions == 0:
                        print(f"[PERMISSION] User {username} has no permissions configured, allowing access to {menu_item_name}")
                        return view_func(request, *args, **kwargs)
                    
                    # Check if user has permission for this specific menu item
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM newapp_menuitem m
                        INNER JOIN newapp_usermenupermission ump ON ump.menu_item_id = m.id
                        WHERE ump.employee_id = %s AND m.name = %s
                    """, [employee_id, menu_item_name])
                    
                    has_permission = cursor.fetchone()[0] > 0
                    
                    if not has_permission:
                        print(f"[PERMISSION] User {username} does not have permission for {menu_item_name}")
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                            return JsonResponse({'status': 'error', 'message': 'You do not have permission to access this page.'}, status=403)
                        messages.error(request, 'You do not have permission to access this page.')
                        return redirect('dashboard')
                    
                    return view_func(request, *args, **kwargs)
                    
            except Exception as e:
                print(f"[PERMISSION] Error: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'message': 'Error checking permissions.'}, status=500)
                messages.error(request, 'Error checking permissions.')
                return redirect('dashboard')
        
        return wrapper
    return decorator


def superuser_required(min_level=1):
    """
    Decorator to check if user is a superuser with at least the specified level.
    
    Args:
        min_level: Minimum superuser level required (1 or 2). Default is 1.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            username = request.session.get('username')
            superuser_level = request.session.get('superuser')
            
            # First check if user is logged in
            if not username:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'message': 'Session expired. Please log in again.'}, status=401)
                messages.error(request, 'Please log in to access this page.')
                return redirect('login')
            
            # Convert superuser_level to int for comparison
            try:
                if superuser_level is None:
                    superuser_level = 0
                else:
                    superuser_level = int(superuser_level)
            except (ValueError, TypeError):
                superuser_level = 0
            
            # Check if user meets minimum superuser level requirement
            if superuser_level < min_level:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'message': 'You do not have permission to access this page.'}, status=403)
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


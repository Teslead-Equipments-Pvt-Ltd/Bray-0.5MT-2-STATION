from django.http import JsonResponse
import json
from bray_app.services.auth_service import AuthService
from django.contrib.auth.hashers import check_password as check_pwd, make_password


def _get_json_or_post(request):
    """
    Helper to support both JSON (fetch with application/json)
    and regular form-encoded POSTs.
    """
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def api_check_username(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"})

    data = _get_json_or_post(request)
    username = data.get("username", "").strip()
    if not username:
        return JsonResponse({"status": "error", "message": "Username required"})

    # Use get_user_by_username to get full user info including status
    row = AuthService.get_user_by_username(username)
    if not row:
        return JsonResponse({"status": "error", "message": "Username not found"})

    name, password, superuser, status = row
    
    # Check if user status is active
    if status != 'active':
        return JsonResponse({
            "status": "error", 
            "message": "Your account is inactive. Please contact admin for assistance."
        })

    return JsonResponse({
        "status": "success", 
        "username": name, 
        "superuser": superuser
    })


def api_login(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"})

    data = _get_json_or_post(request)
    login_identifier = data.get("login_identifier", "").strip()  # Could be username or employee code
    password = data.get("password", "").strip()

    if not login_identifier or not password:
        return JsonResponse({"status": "error", "message": "Missing credentials"})

    # Try to get user by username first
    row = AuthService.get_user_by_username(login_identifier)
    if not row:
        # If not found by username, try by employee code
        row = AuthService.get_user_by_employee_code(login_identifier)
    
    if not row:
        return JsonResponse({'status': 'error', 'message': 'User not found'})

    db_name, db_password, db_superuser, db_status = row

    if not check_pwd(password, db_password):
        return JsonResponse({'status': 'error', 'message': 'Incorrect password'})

    # Check if user status is active
    if db_status != 'active':
        return JsonResponse({
            'status': 'error', 
            'message': 'Your account is inactive. Please contact admin for assistance.'
        })

    request.session['username'] = db_name
    request.session['password'] = db_password
    request.session['superuser'] = db_superuser
    request.session['is_authenticated'] = True
    request.session.modified = True  # Ensure session is saved
    request.session.save()  # Force save session
    
    print(f"[API_LOGIN] Session set - username: {db_name}, superuser: {db_superuser}")
    print(f"[API_LOGIN] Session key: {request.session.session_key}")
    print(f"[API_LOGIN] Session data: {dict(request.session)}")

    # Record login to employee_login_logout_status table and store record ID
    login_record_id = AuthService.record_login(db_name)
    if login_record_id:
        request.session['login_record_id'] = login_record_id

    # Determine superuser status for backward compatibility
    superuser_status = 'yes' if db_superuser > 0 else 'no'

    return JsonResponse({
        'status': 'success',
        'username': db_name,
        'superuser': superuser_status,
        'superuser_level': db_superuser,
        'message': 'Login successful'
    })


def api_check_old_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        old_pwd = data.get('old_password')
        username = request.session.get('username')

        if not username:
            return JsonResponse({'valid': False, 'error': 'Session expired'})

        row = AuthService.get_user_by_username(username)
        if not row:
            return JsonResponse({'valid': False, 'error': 'User not found'})

        _, db_password, _, _ = row
        if check_pwd(old_pwd, db_password):
            return JsonResponse({'valid': True})
        else:
            return JsonResponse({'valid': False, 'error': 'Incorrect password'})

    except Exception as e:
        return JsonResponse({'valid': False, 'error': str(e)})


def api_logout(request):
    """
    API endpoint for logout functionality.
    Clears session and updates logout status in database.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    try:
        username = request.session.get('username')
        print(f"[API_LOGOUT] Username from session: {username}")

        # Record logout to employee_login_logout_status table BEFORE clearing session
        login_record_id = request.session.get('login_record_id')
        if username:
            result = AuthService.record_logout(username, login_record_id)
            print(f"[API_LOGOUT] record_logout result: {result}")
        else:
            print("[API_LOGOUT] No username in session, skipping logout record")

        # Clear session AFTER recording logout
        request.session.flush()

        return JsonResponse({
            'status': 'success',
            'message': 'Logout successful'
        })

    except Exception as e:
        print(f"[API_LOGOUT] Error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def api_check_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            old_password = data.get('old_password')
            employee_username = request.session.get('username')

            if not employee_username:
                return JsonResponse({'valid': False, 'error': 'Session expired'})

            row = AuthService.get_user_by_username(employee_username)

            if not row:
                return JsonResponse({'valid': False, 'error': 'User not found'})

            _, db_password, _, _ = row
            # Use Django's check_password to verify hashed password
            if check_pwd(old_password, db_password):
                return JsonResponse({'valid': True})
            else:
                return JsonResponse({'valid': False, 'error': 'Old password is incorrect'})
        except Exception as e:
            return JsonResponse({'valid': False, 'error': f'Server error: {str(e)}'})
    return JsonResponse({'error': 'Invalid method'}, status=405)


def api_change_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()

        employee_username = request.session.get('username')
        if not employee_username:
            return JsonResponse({'error': 'Session expired. Please log in again.'}, status=401)

        if not old_password or not new_password:
            return JsonResponse({'error': 'Old password and new password are required.'}, status=400)

        row = AuthService.get_user_by_username(employee_username)

        if not row:
            return JsonResponse({'error': 'User not found.'}, status=404)

        _, db_password, _, _ = row

        if not check_pwd(old_password, db_password):
            return JsonResponse({'error': 'Old password is incorrect.'}, status=400)

        hashed_password = make_password(new_password)
        AuthService.update_password(employee_username, hashed_password)
        
        request.session['password'] = hashed_password

        return JsonResponse({'success': True, 'message': 'Password updated successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error updating password: {str(e)}'}, status=500)


def api_validate_employee_code(request):
    """Validate employee code for regular users (superuser = 0)"""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"})

    data = _get_json_or_post(request)
    username = data.get("username", "").strip()
    employee_code = data.get("employee_code", "").strip()

    if not username or not employee_code:
        return JsonResponse({"status": "error", "message": "Username and employee code required"})

    # Validate employee code matches the user
    if AuthService.validate_employee_code(username, employee_code):
        return JsonResponse({"status": "success", "message": "Employee code validated"})
    else:
        return JsonResponse({"status": "error", "message": "Invalid employee code"})


def api_check_employee_code(request):
    """Check if employee code exists and get user info"""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"})

    data = _get_json_or_post(request)
    employee_code = data.get("employee_code", "").strip()
    
    if not employee_code:
        return JsonResponse({"status": "error", "message": "Employee code required"})

    # Get user by employee code
    row = AuthService.get_user_by_employee_code(employee_code)
    if not row:
        return JsonResponse({"status": "error", "message": "Employee code not found"})

    name, password, superuser, status = row
    
    # Check if user status is active
    if status != 'active':
        return JsonResponse({
            "status": "error", 
            "message": "Your account is inactive. Please contact admin for assistance."
        })

    return JsonResponse({
        "status": "success", 
        "username": name, 
        "superuser": superuser
    })
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password as check_pwd
from bray_app.services.auth_service import AuthService
 

def _require_session_auth(request):
    """
    Simple guard using our custom session flag set by api_login.
    Redirects to the login page if not authenticated.
    """
    is_auth = request.session.get("is_authenticated")
    username = request.session.get("username")
    superuser = request.session.get("superuser")
    print(f"[SESSION_AUTH] is_authenticated: {is_auth}, username: {username}, superuser: {superuser}")
    print(f"[SESSION_AUTH] Session keys: {list(request.session.keys())}")
    print(f"[SESSION_AUTH] Request path: {request.path}")
    
    if not is_auth or not username:
        print("[SESSION_AUTH] Not authenticated, redirecting to login")
        return redirect("login")
    print(f"[SESSION_AUTH] User {username} is authenticated, allowing access")
    return None


def root_redirect(request):
    """
    Root URL handler - redirects to dashboard if authenticated, otherwise to login.
    """
    is_auth = request.session.get("is_authenticated")
    username = request.session.get("username")
    print(f"[ROOT_REDIRECT] is_authenticated: {is_auth}, username: {username}")
    
    if is_auth and username:
        print(f"[ROOT_REDIRECT] Redirecting to dashboard")
        return redirect("dashboard")
    print(f"[ROOT_REDIRECT] Redirecting to login")
    return redirect("login")


def login_page(request):
    # If already authenticated, redirect to dashboard
    is_auth = request.session.get("is_authenticated")
    username = request.session.get("username")
    print(f"[LOGIN_PAGE] Checking auth - is_authenticated: {is_auth}, username: {username}")
    
    if is_auth and username:
        print(f"[LOGIN_PAGE] User {username} already authenticated, redirecting to dashboard")
        return redirect("dashboard")
    
    # Only flush session if user is not authenticated
    print("[LOGIN_PAGE] User not authenticated, showing login page")
    request.session.flush()
    request.session["is_authenticated"] = False
    request.session["referer"] = request.META.get("HTTP_REFERER", "/")
    return render(request, "new_login.html")


def dashboard(request):
    # Protect with our custom session-based auth
    guard = _require_session_auth(request)
    if guard:
        return guard

    # Get last login time for the current user
    username = request.session.get("username")
    last_login = AuthService.get_last_login(username)
    
    # Format last login for display
    last_login_display = "Never"
    if last_login:
        from datetime import datetime
        now = datetime.now()
        if hasattr(last_login, 'replace'):
            # It's a datetime object
            diff = now - last_login
        else:
            # It's a string, parse it
            try:
                last_login_dt = datetime.strptime(str(last_login), '%Y-%m-%d %H:%M:%S')
                diff = now - last_login_dt
            except:
                diff = None
        
        if diff:
            total_seconds = int(diff.total_seconds())
            if total_seconds < 60:
                last_login_display = "Just now"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                last_login_display = f"{minutes} min ago"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                last_login_display = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                days = total_seconds // 86400
                last_login_display = f"{days} day{'s' if days > 1 else ''} ago"

    return render(request, "dashboard_new.html", {"last_login": last_login_display})


def change_password(request):
    # Protect with our custom session-based auth
    guard = _require_session_auth(request)
    if guard:
        return guard
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        username = request.session.get("username")
        if not username:
            messages.error(request, "Session expired. Please login again.")
            return redirect('login')

        row = AuthService.get_user_by_username(username)
        if not row:
            messages.error(request, "User not found.")
            return redirect('login')

        _, db_password, _ = row

        if not check_pwd(old_password, db_password):
            messages.error(request, "Old password incorrect.")
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, "New and confirm password mismatch.")
            return redirect('change_password')

        hashed = make_password(new_password)
        AuthService.update_password(username, hashed)

        messages.success(request, "Password updated.")
        return redirect('dashboard')

    return render(request, 'dashboard.html')


def logout_view(request):  
    username = request.session.get('username')
    password = request.session.get('password')

    if username and password:
        AuthService.update_logout(username, password)

    request.session.flush()
    request.session['logout_message'] = "Logout successful"

    return redirect('login')

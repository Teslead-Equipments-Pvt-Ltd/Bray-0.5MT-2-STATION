# URL Routing Flow Documentation

## Overview
This document explains how URLs are routed from `bray_soft/urls.py` to all HTML render endpoints and API endpoints in the application.

---

## 📋 Table of Contents
1. [Main URL Configuration](#main-url-configuration)
2. [Page URLs (HTML Rendering)](#page-urls-html-rendering)
3. [API URLs (JSON Responses)](#api-urls-json-responses)
4. [Complete Flow Diagram](#complete-flow-diagram)
5. [Request Flow Examples](#request-flow-examples)

---

## 1. Main URL Configuration

**File:** `bray_soft/urls.py`

This is the **root URL configuration** that Django uses to route all incoming requests.

```python
urlpatterns = [
    # Root URL - redirect to login or dashboard based on auth status
    path("", root_redirect, name="root"),
    
    # Page URLs (HTML rendering)
    path("", include("bray_app.urls.pages.auth_page_urls")),
    path("", include("bray_app.urls.pages.standards_page_urls")),
   

    # Django default login redirect handler
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False)),

    # API URLs (JSON responses)
    path("api/", include("bray_app.urls.api.standards_api_urls")),
    path("api/auth/", include("bray_app.urls.api.auth_api_urls")),
]
```

### URL Pattern Matching Order:
Django matches URLs **in order** from top to bottom. The first match wins!

---

## 2. Page URLs (HTML Rendering)

These endpoints render HTML templates to the browser.

### 2.1 Authentication Pages

**File:** `bray_app/urls/pages/auth_page_urls.py`

| URL Pattern | View Function | Template | Description |
|------------|---------------|----------|-------------|
| `/login/` | `login_page` | `new_login.html` | Login page (clears session) |
| `/dashboard/` | `dashboard` | `dashboard_new.html` | Main dashboard (protected) |
| `/change-password/` | `change_password` | `dashboard.html` | Change password page (protected) |
| `/logout/` | `logout_view` | Redirects to login | Logout and clear session |

**Flow:**
```
User Request: GET /login/
    ↓
bray_soft/urls.py (matches path="", includes auth_page_urls)
    ↓
bray_app/urls/pages/auth_page_urls.py (matches path='login/')
    ↓
bray_app/views/pages/auth_page_views.py → login_page()
    ↓
Renders: new_login.html
```

### 2.2 Standards Pages

**File:** `bray_app/urls/pages/standards_page_urls.py`

| URL Pattern | View Function | Template | Description |
|------------|---------------|----------|-------------|
| `/standards/` | `standard_list_page` | `standard_list.html` | List all standards (protected) |

**Flow:**
```
User Request: GET /standards/
    ↓
bray_soft/urls.py (matches path="", includes standards_page_urls)
    ↓
bray_app/urls/pages/standards_page_urls.py (matches path="standards/")
    ↓
bray_app/views/pages/standards_page_views.py → standard_list_page()
    ↓
@permission_required("Standard") decorator checks permissions
    ↓
Renders: standard_list.html with standards data
```

### 2.3 Root URL Handler

**Special Case:** `path("", root_redirect, name="root")`

| URL Pattern | View Function | Action |
|------------|---------------|--------|
| `/` | `root_redirect` | Redirects based on auth status |

**Flow:**
```
User Request: GET /
    ↓
bray_soft/urls.py (matches path="", root_redirect)
    ↓
bray_app/views/pages/auth_page_views.py → root_redirect()
    ↓
Checks: request.session.get("is_authenticated")
    ↓
If authenticated → redirect("/dashboard/")
If not authenticated → redirect("/login/")
```

---

## 3. API URLs (JSON Responses)

These endpoints return JSON data (used by JavaScript fetch calls).

### 3.1 Authentication API

**File:** `bray_app/urls/api/auth_api_urls.py`

| URL Pattern | View Function | Method | Description |
|------------|---------------|--------|-------------|
| `/api/auth/check-username/` | `api_check_username` | POST | Verify username exists |
| `/api/auth/login/` | `api_login` | POST | Authenticate user, set session |
| `/api/auth/check-old-password/` | `api_check_old_password` | POST | Verify old password |

**Flow Example (Login):**
```
JavaScript: fetch("/api/auth/login/", {method: "POST", body: JSON.stringify({username, password})})
    ↓
bray_soft/urls.py (matches path="api/auth/", includes auth_api_urls)
    ↓
bray_app/urls/api/auth_api_urls.py (matches path='login/')
    ↓
bray_app/views/api/auth_api_views.py → api_login()
    ↓
Validates credentials → Sets session → Returns JSON response
    ↓
Response: {"status": "success", "username": "...", "superuser": "yes/no"}
```

### 3.2 Standards API

**File:** `bray_app/urls/api/standards_api_urls.py`

| URL Pattern | View Function | Method | Description |
|------------|---------------|--------|-------------|
| `/api/standards/add/` | `add_standard_api` | POST | Add new standard |
| `/api/standards/edit/<id>/` | `edit_standard_api` | POST | Update standard |
| `/api/standards/delete/<id>/` | `delete_standard_api` | POST | Delete standard |

**Flow Example (Add Standard):**
```
JavaScript: fetch("/api/standards/add/", {method: "POST", body: FormData})
    ↓
bray_soft/urls.py (matches path="api/", includes standards_api_urls)
    ↓
bray_app/urls/api/standards_api_urls.py (matches path="standards/add/")
    ↓
bray_app/views/api/standards_api_views.py → add_standard_api()
    ↓
@permission_required("Standard") decorator checks permissions
    ↓
Validates data → Calls service → Returns JSON response
    ↓
Response: {"message": "Standard added", "id": 123}
```

---

## 4. Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Browser Request                      │
│              http://localhost:8000/<path>                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           bray_soft/urls.py (ROOT URLCONF)               │
│                                                              │
│  URL Pattern Matching (in order):                           │
│  1. path("", root_redirect)                                  │
│  2. path("", include("standards_page_urls"))                │
│  3. path("", include("auth_page_urls"))                     │
│  4. path("accounts/login/", RedirectView...)                │
│  5. path("api/", include("standards_api_urls"))              │
│  6. path("api/auth/", include("auth_api_urls"))              │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
┌──────────────────────┐          ┌──────────────────────┐
│   PAGE URLS          │          │     API URLS         │
│  (HTML Rendering)    │          │   (JSON Responses)   │
└──────────────────────┘          └──────────────────────┘
        │                                     │
        ▼                                     ▼
┌──────────────────────┐          ┌──────────────────────┐
│ auth_page_urls.py    │          │ auth_api_urls.py     │
│ standards_page_urls  │          │ standards_api_urls   │
└──────────────────────┘          └──────────────────────┘
        │                                     │
        ▼                                     ▼
┌──────────────────────┐          ┌──────────────────────┐
│  VIEW FUNCTIONS      │          │  API VIEW FUNCTIONS   │
│  (auth_page_views)   │          │  (auth_api_views)     │
│  (standards_page_    │          │  (standards_api_views)│
│   views)             │          │                        │
└──────────────────────┘          └──────────────────────┘
        │                                     │
        ▼                                     ▼
┌──────────────────────┐          ┌──────────────────────┐
│  RENDER TEMPLATES    │          │  RETURN JSON         │
│  (HTML files)        │          │  (JsonResponse)      │
└──────────────────────┘          └──────────────────────┘
```

---

## 5. Request Flow Examples

### Example 1: User Visits Root URL

```
1. User types: http://localhost:8000/
   
2. Django receives request → checks bray_soft/urls.py
   
3. Matches: path("", root_redirect, name="root")
   
4. Calls: root_redirect(request)
   - Checks: request.session.get("is_authenticated")
   - If True → redirect("/dashboard/")
   - If False → redirect("/login/")
   
5. Browser follows redirect to /login/ or /dashboard/
```

### Example 2: User Logs In (Complete Flow)

```
STEP 1: User visits /login/
   Request: GET /login/
   → bray_soft/urls.py
   → auth_page_urls.py (path='login/')
   → login_page() view
   → Renders: new_login.html

STEP 2: User enters username, clicks "Next"
   JavaScript: fetch("/api/auth/check-username/", {method: "POST", body: JSON.stringify({username})})
   → bray_soft/urls.py
   → path("api/auth/", include("auth_api_urls"))
   → auth_api_urls.py (path='check-username/')
   → api_check_username() view
   → Returns: {"status": "success", "username": "...", "superuser": "..."}

STEP 3: User enters password, clicks "Next"
   JavaScript: fetch("/api/auth/login/", {method: "POST", body: JSON.stringify({username, password})})
   → bray_soft/urls.py
   → path("api/auth/", include("auth_api_urls"))
   → auth_api_urls.py (path='login/')
   → api_login() view
   → Validates password
   → Sets session: request.session['is_authenticated'] = True
   → Returns: {"status": "success", "username": "...", "superuser": "..."}

STEP 4: JavaScript redirects to dashboard
   window.location.href = "/dashboard/"
   → bray_soft/urls.py
   → auth_page_urls.py (path='dashboard/')
   → dashboard() view
   → Checks: _require_session_auth(request)
   → Renders: dashboard_new.html
```

### Example 3: User Views Standards List

```
1. User clicks "Standard" in sidebar menu
   → JavaScript: window.location.href = "/standard/"
   
2. Django receives: GET /standard/
   → bray_soft/urls.py (no match for /standard/)
   → 404 Not Found
   
   ⚠️ NOTE: The actual URL is /standards/ (with 's')
   
3. Correct flow: GET /standards/
   → bray_soft/urls.py
   → standards_page_urls.py (path="standards/")
   → standard_list_page() view
   → @permission_required("Standard") checks permissions
   → Calls: get_all_standards() service
   → Renders: standard_list.html with standards data
```

### Example 4: User Adds a Standard (API Call)

```
1. User fills form in modal, clicks "Save"
   
2. JavaScript: fetch("/api/standards/add/", {
     method: "POST",
     headers: {"X-CSRFToken": csrfToken},
     body: FormData
   })
   
3. Django receives: POST /api/standards/add/
   → bray_soft/urls.py
   → path("api/", include("standards_api_urls"))
   → standards_api_urls.py (path="standards/add/")
   → add_standard_api() view
   → @permission_required("Standard") checks permissions
   → Validates: name, description
   → Checks: duplicate name
   → Calls: insert_standard() service
   → Returns: {"message": "Standard added", "id": 123}
   
4. JavaScript receives response
   → If success → location.reload()
   → If error → alert(res.error)
```

---

## 6. Important Notes

### URL Matching Priority
- Django matches URLs **in the order they appear** in `urlpatterns`
- The **first match wins**, so order matters!
- More specific patterns should come before general ones

### Authentication Flow
- **Page views** use `_require_session_auth()` to check `request.session['is_authenticated']`
- **API views** use `@permission_required()` decorator to check permissions
- Session is set by `api_login()` when user successfully logs in

### CSRF Protection
- All POST requests require CSRF token
- Page templates include `{% csrf_token %}` in forms
- JavaScript fetch calls include `X-CSRFToken` header
- Token can be retrieved from hidden input or cookie

### Template Inheritance
- All page templates extend `base_new.html`
- `base_new.html` provides sidebar, header, and common scripts
- Child templates override `{% block content %}` and `{% block header_title %}`

---

## 7. File Structure Summary

```
bray_soft/
├── urls.py                          # ROOT URL configuration
│
bray_app/
├── urls/
│   ├── pages/
│   │   ├── auth_page_urls.py        # /login/, /dashboard/, etc.
│   │   └── standards_page_urls.py   # /standards/
│   └── api/
│       ├── auth_api_urls.py        # /api/auth/check-username/, etc.
│       └── standards_api_urls.py   # /api/standards/add/, etc.
│
└── views/
    ├── pages/
    │   ├── auth_page_views.py       # HTML rendering views
    │   └── standards_page_views.py  # HTML rendering views
    └── api/
        ├── auth_api_views.py        # JSON response views
        └── standards_api_views.py   # JSON response views
```

---

## 8. Quick Reference

### All Available URLs

**Page URLs (HTML):**
- `/` → Redirects to login or dashboard
- `/login/` → Login page
- `/dashboard/` → Dashboard (protected)
- `/change-password/` → Change password (protected)
- `/logout/` → Logout and redirect to login
- `/standards/` → Standards list page (protected)
- `/accounts/login/` → Redirects to `/login/`

**API URLs (JSON):**
- `/api/auth/check-username/` → Verify username (POST)
- `/api/auth/login/` → Login user (POST)
- `/api/auth/check-old-password/` → Verify old password (POST)
- `/api/standards/add/` → Add standard (POST)
- `/api/standards/edit/<id>/` → Edit standard (POST)
- `/api/standards/delete/<id>/` → Delete standard (POST)

---

**End of Documentation**


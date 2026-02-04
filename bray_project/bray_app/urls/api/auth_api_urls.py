from django.urls import path
from bray_app.views.api.auth_api_views import (
    api_check_username,
    api_login,
    api_check_old_password,
    api_logout,
    api_check_password,
    api_change_password,
    api_validate_employee_code,
    api_check_employee_code
)

urlpatterns = [
    path('check-username/', api_check_username, name='api_check_username'),
    path('check-employee-code/', api_check_employee_code, name='api_check_employee_code'),
    path('login/', api_login, name='api_login'),
    path('logout/', api_logout, name='api_logout'),
    path('check-old-password/', api_check_old_password, name='api_check_old_password'),
    path('check_password/',api_check_password,name='api_check_password'),
    path('change_password/',api_change_password,name='change_password'),
    path('validate-employee-code/', api_validate_employee_code, name='api_validate_employee_code'),
]

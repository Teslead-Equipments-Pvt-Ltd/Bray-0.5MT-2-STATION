from django.urls import path
from bray_app.views.api.employee_api_views import (
    get_all_employees_api,
    get_employee_api,
    add_employee_api,
    edit_employee_api,
    delete_employee_api,
    bulk_delete_employees_api,
)

urlpatterns = [
    path("", get_all_employees_api, name="api_get_all_employees"),
    path("<int:pk>/", get_employee_api, name="api_get_employee"),
    path("add/", add_employee_api, name="api_add_employee"),
    path("edit/<int:pk>/", edit_employee_api, name="api_edit_employee"),
    path("delete/<int:pk>/", delete_employee_api, name="api_delete_employee"),
    path("bulk_delete/", bulk_delete_employees_api, name="api_bulk_delete_employees"),
]

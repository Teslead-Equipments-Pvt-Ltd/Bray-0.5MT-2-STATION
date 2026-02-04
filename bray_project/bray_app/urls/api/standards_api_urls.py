from django.urls import path
from bray_app.views.api.standards_api_views import (
    get_all_standards_api,
    add_standard_api,
    edit_standard_api,
    delete_standard_api,
    bulk_delete_standards_api
)

urlpatterns = [
    path("standards/", get_all_standards_api, name="api_get_all_standards"),
    path("standards/add/", add_standard_api),
    path("standards/edit/<int:pk>/", edit_standard_api),
    path("standards/delete/<int:pk>/", delete_standard_api),
    path("standards/bulk_delete/", bulk_delete_standards_api)
]

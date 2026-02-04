from django.urls import path
from bray_app.views.api.testtype_api_views import (
    get_all_testtypes_api,
    update_testtypes_api,
)

urlpatterns = [
    # GET - list all test types and supporting data
    path("testtypes/", get_all_testtypes_api, name="api_get_all_testtypes"),

    # POST - bulk update test types (same semantics as existing POST form)
    path("testtypes/update/", update_testtypes_api, name="api_update_testtypes"),
]



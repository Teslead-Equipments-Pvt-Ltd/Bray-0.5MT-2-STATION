from django.urls import path
from bray_app.views.api.valvetype_api_views import (
    get_all_valve_types_api,
    valve_type_add_api,
    valve_type_edit_api,
    valve_type_delete_api,
    bulk_delete_valvetype_api
)

urlpatterns = [
    # GET - list all valve types and supporting data
    path("", get_all_valve_types_api, name="valve_type_list"),

    # POST - CRUD operations
    path("add/", valve_type_add_api, name="valve_type_add"),
    path("edit/<int:valve_type_id>/", valve_type_edit_api, name="valve_type_edit"),
    path("delete/<int:valve_type_id>/", valve_type_delete_api, name="valve_type_delete"),
    path("bulk_delete/", bulk_delete_valvetype_api, name="valve_type_bulk_delete"),
]
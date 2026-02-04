from django.urls import path
from bray_app.views.api.valve_class_api_views import (
    get_all_valve_classes_api,
    add_valve_class_api,
    edit_valve_class_api,
    delete_valve_class_api,
    bulk_delete_valve_classes_api
)

urlpatterns = [
    path("valve_class/", get_all_valve_classes_api, name="api_get_all_valve_classes"),
    path("valve_class/add/", add_valve_class_api),
    path("valve_class/edit/<int:pk>/", edit_valve_class_api),
    path("valve_class/delete/<int:pk>/", delete_valve_class_api),
    path("valve_class/bulk_delete/", bulk_delete_valve_classes_api),
]

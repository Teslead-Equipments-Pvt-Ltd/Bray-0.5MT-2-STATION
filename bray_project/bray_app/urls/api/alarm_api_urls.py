from django.urls import path
from bray_app.views.api.alarm_api_views import (
    alarm_list_api,
    alarm_add_api,
    alarm_edit_api,
    alarm_delete_api,
    alarm_detail_api
)

urlpatterns = [
    path("", alarm_list_api, name="alarm_list_api"),
    path("add/", alarm_add_api, name="alarm_add_api"),
    path("edit/<int:alarm_id>/", alarm_edit_api, name="alarm_edit_api"),
    path("delete/<int:alarm_id>/", alarm_delete_api, name="alarm_delete_api"),
    path("detail/<int:alarm_id>/", alarm_detail_api, name="alarm_detail_api"),
]
from django.urls import path
from bray_app.views.api.gauge_details_api_views import (
    get_all_gauges_api,
    add_gauge_api,
    edit_gauge_api,
    delete_gauge_api,
    check_serial_exists_api,
    save_gauges_api
)

urlpatterns = [
    path("gauge_details/", get_all_gauges_api, name="api_get_all_gauges"),
    path("gauge_details/add/", add_gauge_api),
    path("gauge_details/edit/<int:pk>/", edit_gauge_api),
    path("gauge_details/delete/<int:pk>/", delete_gauge_api),
    path("gauge_details/check-serial/", check_serial_exists_api),
    path("gauge_details/save/", save_gauges_api),
]

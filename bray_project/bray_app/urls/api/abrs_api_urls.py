"""
ABRS API URL Configuration
"""
from django.urls import path
from bray_app.views.api.abrs_api_views import (
    api_import_by_date,
    api_import_by_serial,
    api_search_serials,
    api_serial_details,
    api_sync_by_single_date,
    api_get_abrs_table_data,
    api_update_status,
    api_get_assembly,
    api_push_data
)

urlpatterns = [
    path('table-data/', api_get_abrs_table_data, name='api_abrs_table_data'),
    path('import-by-date/', api_import_by_date, name='api_abrs_import_by_date'),
    path('import-by-serial/', api_import_by_serial, name='api_abrs_import_by_serial'),
    path('search-serials/', api_search_serials, name='api_abrs_search_serials'),
    path('serial-details/<str:serial_number>/', api_serial_details, name='api_abrs_serial_details'),
    path('sync-by-date/', api_sync_by_single_date, name='api_abrs_sync_by_date'),
    path('update-status/', api_update_status, name='api_abrs_update_status'),
    path('get-assembly/', api_get_assembly, name='api_abrs_get_assembly'),
    path('push-data/', api_push_data, name='api_abrs_push_data'),
]

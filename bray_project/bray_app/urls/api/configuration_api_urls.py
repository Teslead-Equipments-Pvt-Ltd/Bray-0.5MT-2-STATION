from django.urls import path
from bray_app import views
from bray_app.views.api.configuration_api_views import get_abrs_values, get_hmi_api, save_abrs_field, save_report_path, update_backup_toggle,update_graph_toggle, update_pdf_toggle, update_csv_toggle, get_all_toggle, connect_hmi, connect_abrs

urlpatterns = [
    path("get_hmi_status/", get_hmi_api, name="get_hmi_status"),
    path('update_graph_toggle/', update_graph_toggle, name='update_graph_toggle'),
    path('update_pdf_toggle/', update_pdf_toggle, name='update_pdf_toggle'),
    path('update_csv_toggle/', update_csv_toggle, name='update_csv_toggle'),
    path('update_backup_toggle/', update_backup_toggle, name='update_backup_toggle'),
    path('get_graph_toggle/', get_all_toggle, name='get_all_toggle'),
    path('save_report_path/', save_report_path, name='save_report_path'),
    path('save_abrs_field/', save_abrs_field, name='save_abrs_field'),
    path('get_abrs_values/', get_abrs_values, name='get_abrs_values'),
    path('connect_hmi/', connect_hmi, name='connect_hmi'),
    path('connect_abrs/', connect_abrs, name='connect_abrs'),
]
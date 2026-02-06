from django.urls import path
from bray_app.views.api.valve_serial_api_views import (
    check_assembly_id, 
    get_assembly_id, 
    delete_and_retest_serial, 
    save_to_local_db,
    fetch_and_save_assembly
)

urlpatterns = [
    path('check_assembly_id/', check_assembly_id, name='check_assembly_id'),
    path('get_assembly_id/', get_assembly_id, name='get_assembly_id'),
    path('delete_and_retest_serial/', delete_and_retest_serial, name='delete_and_retest_serial'),
    path('save_to_local_db/', save_to_local_db, name='save_to_local_db'),
    path('fetch_and_save_assembly/', fetch_and_save_assembly, name='fetch_and_save_assembly'),
]
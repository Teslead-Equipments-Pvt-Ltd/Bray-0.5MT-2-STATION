from django.urls import path

from bray_app.views.api.syncpage_api_views import(
    sync_check_status,
    auto_test,
    sync_enabled_test_buttons,
    get_station_values,
    get_set_pressure,
    sync_live_values,
    get_sync_history_values,
    delete_and_retest,
    save_tested_values,
    test_result_status,
    cycle_complete,
    reset_all_station,
)


urlpatterns = [

    path('api/syncpage_api/check_status/', sync_check_status, name='check_status'),
    path('api/syncpage_api/auto_station_action/<str:stationNum>/',auto_test, name='test_mode_selection'),
    path('api/syncpage_api/enabled_test_buttons/<str:stationId>/',sync_enabled_test_buttons, name='sync_enabled_test_buttons'),
    path('api/syncpage_api/get_station_values/<str:stationId>/',get_station_values, name='get_station_values'),
    path('api/syncpage_api/get_test_values/<str:stationId>/<int:id>/<str:name>/<str:valve_serial_no>/<str:psr_unit>/', get_set_pressure, name='get_set_pressure'),
    path('api/syncpage_api/sync_station_live/<str:stationId>/<int:id>/<str:valve_serial_no>/', sync_live_values, name='get_live_values'),
    path('api/syncpage_api/get_history_values/<int:stationNum>/<int:testId>/<str:valve_serial_no>/', get_sync_history_values, name='get_history_values'),
    path('api/syncpage_api/test_result_status/<int:stationNum>/<str:valve_serial_no>/', test_result_status, name='test_result_status'),
    path('api/syncpage_api/save_final_values/<int:testId>/<str:valve_serial_no>/<int:stationNum>/', save_tested_values, name = 'save_tested_values'),
    path('api/delete_test_data/<int:stationNum>/<int:testId>/<str:valve_serial_no>/', delete_and_retest, name='delete_test_data'),
    
    path('api/syncpage_api/cyclecomplete/', cycle_complete, name='cycle_complete'),
    path('api/syncpage_api/reset_all_station/', reset_all_station, name='reset_all_station'),
    
   
]
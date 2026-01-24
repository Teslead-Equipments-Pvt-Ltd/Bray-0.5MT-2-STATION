from django.shortcuts import render
from django.urls import path

from bray_app.views.api.single_live_page_api_views import (
    check_status,
    # check_connection,
    check_abrs_hmi_connection,
    getStation_values,
    enabled_test_buttons,
    get_test_set_pressure,
    station_live_values,
    get_history_values,
    delete_and_retest,
    save_initial_pressure,
    save_final_pressure,
    delete_incomplete_test,
    cycle_complete,
    auto_test_select,
    get_test_result_status,
    
)





urlpatterns = [
    #station 1
    path('auto_station_action/<int:stationNum>/',auto_test_select, name='test_mode_selection'),
    path('check_status/',check_status, name='get_hmi_pressure'),
    path('check_abrs_hmi_connection/',check_abrs_hmi_connection, name='check_connection' ),
    # path('station_values/',getStation_values,name='station1_values'),
    path('station_values/<int:stationNum>/',getStation_values,name='station_values'),
    path('get_enabled_tst_btns/', enabled_test_buttons,name='enabled_tst_btns'),
    path('get_test_values/<int:id>/<str:valve_serial_no>/<str:name>/<int:stationNum>/<str:units>/', get_test_set_pressure,name='test_values'),

    # path('get_pressure_data/<int:id>/<str:valve_serial_no>/',get_pressure_data, name='get_stored_pressure_data'),

    # path('get_live_pressure_data/<int:id>/<str:valve_serial_no>/<int:currentStation>',get_live_pressure_data, name='get_stored_pressure_data'),
    path('station/<int:stationNum>/<int:testId>/<str:valve_serial_no>/history/',get_history_values,name='get_stored_pressure_data'),
    path('station/<int:stationNum>/<int:id>/<str:valve_serial_no>/live/',station_live_values,name='get_history_data'),

    path('delete_test_data/<int:stationNum>/<int:testId>/<str:valve_serial_no>/',delete_and_retest ,name='delete_previous'),

    path('save_initial_pressure/<int:id>/<str:valve_serial_no>/<int:stationNum>/',save_initial_pressure, name='start_prssuer'),
    path('save_final_pressure/<int:testId>/<str:valve_serial_no>/<int:stationNum>/',save_final_pressure, name='end_prssuer_with_result'),

    path('dashboard/delete_incomplete_test/<int:stationNum>/<str:serialNo>/',delete_incomplete_test,name='delete_old_test'),


    path('cyclecomplete/<int:stationNum>/<str:valveSerial>/',cycle_complete, name='test_complete' ),

    path('test_result_status/<int:stationNum>/<str:valve_serial_no>/',get_test_result_status, name='get_test_result_status'),


]
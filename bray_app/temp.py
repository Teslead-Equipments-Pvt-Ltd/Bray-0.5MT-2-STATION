# """
# URL configuration for brayproject project.

# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/5.2/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """
# from django.contrib import admin
# from django.urls import path
# from bray_app import views

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', views.login, name='login'),
    
#     path('new_username/', views.new_username, name='new_username'),
#     path('new_pwd/', views.new_pwd, name='new_pwd'),
#     path('change_password/', views.change_password, name='change_password'),
#     path('check_password/', views.check_password, name='check_password'),
    
#     path('dashboard/', views.dashboard, name='dashboard'),
#     path('logout/', views.custom_logout, name='logout'),
    
#     path('standard/', views.standard_list, name='standard_list'),
#     path('standard/add/', views.add_standard, name='add_standard'),
#     path('standard/edit/<int:pk>/', views.edit_standard, name='edit_standard'),
#     path('standard/delete/<int:pk>/', views.delete_standard, name='delete_standard'),
#     path('valve_size/', views.valve_size_list, name='valve_size_list'),
#     path('delete/<int:pk>/', views.valve_size_delete, name='valve_size_delete'),
#      path('valve_class/', views.valve_class_list, name='valve_class'),
  

#      path('valve_class/delete/<int:pk>/', views.valve_class_delete, name='valve_class_delete'),
#      path('valve_type/', views.valve_type_list, name='valve_type'),
#      path('valve_type/delete/<int:valve_type_id>/', views.valve_type_delete, name='valve_type_delete'),
#      path('shell_material/', views.shell_material, name='shell_material'),
#      path('shell_material_delete/<int:pk>/', views.shell_material_delete, name='shell_material_delete'),
#      path('employee/', views.employee, name='employee'),
#      path('employee/add/', views.employee_add, name='employee_add'),
#      path('employee/edit/<int:id>/', views.employee_edit, name='employee_edit'),
#      path('employee/delete/<int:id>/', views.employee_delete, name='employee_delete'),
#      path('gauge_details/', views.gauge_details, name='gauge_details'),
#     path('gauge-save/', views.gauge_save, name='gauge_save'),
#     path('gauge-delete/<int:instrument_id>/', views.gauge_delete, name='gauge_delete'),
#      path('instrument_type/', views.instrument_type, name='instrument_type'),
#      path('instrument-type-delete/<int:instrument_type_id>/', views.instrument_type_delete, name='instrument_type_delete'),
#      path('graph/',views.graph,name='graph'),
#      path('vtr/', views.vtr, name='vtr'),
#     path('user_permissions_view/', views.user_permissions_view, name='user_permissions_view'),
#     path('abrs/',views.abrs,name='abrs'),
#     path('user_accounting/',views.user_accounting,name='user_accounting'),
#     path('user_anable_disable/',views.user_anable_disable,name='user_anable_disable'),
#     path('user_config/',views.user_config,name='user_config'),

#     path('livepage',views.livepage,name='livepage'),
#     path('dummy',views.dummy,name='dummy'),
#     path('getpressure_duration/',views.getpressure_duration,name='getpressure_duration'),
#     path('save_station1/',views.save_station1,name='save_station1'),
#     path('save_station2/',views.save_station2,name='save_station2'),
#     path('stationnew',views.stationnew,name='stationnew'),
#     path('disable_indb/',views.disable_indb,name='disable_indb'),
#     path('disable2_indb/',views.disable2_indb,name='disable2_indb'),
#     path('category/', views.category, name='category'),
#     path('toggle_field/',views.toggle_field,name='toggle_field'),

#     path('get_hmi_abrs/',views.get_hmi_abrs,name="get_hmi_abrs"),
#     path('test_result/',views.test_result,name='test_result'),
#     path('pdf/',views.pdf,name='pdf'),


#     path('inactive_station1/',views.inactive_station1,name="inactive_station1"),
#     path('inactive_station2/',views.inactive_station2,name="inactive_station2"),
#     path('check_status/',views.check_status,name='check_status'),
#     path('get_pressure/', views.get_pressure, name='get_pressure'),

#     path('station1_values/',views.getStation1_values,name='station1_values'),
#     path('station2_values/',views.getStation2_values,name='station2_values'),

#      path('get_pressure_data1/', views.get_pressure_data1, name='get_pressure_data1'),
#      path('get_stored_pressure_data/', views.get_stored_pressure_data, name='get_stored_pressure_data'),
     
#      path('test_type/', views.test_type, name='test_type'),
#      path('update_graph_toggle/', views.update_graph_toggle, name='update_graph_toggle'),
#      path('update_pdf_toggle/', views.update_pdf_toggle, name='update_pdf_toggle'),
#      path('update_csv_toggle/', views.update_csv_toggle, name='update_csv_toggle'),
#      path('update_backup_toggle/', views.update_backup_toggle, name='update_backup_toggle'),
#      path('get_graph_toggle/', views.get_graph_toggle, name='get_graph_toggle'),
#      path('save_report_path/', views.save_report_path, name='save_report_path'),
#      path('save_abrs_field/', views.save_abrs_field, name='save_abrs_field'),
#      path('get_abrs_values/', views.get_abrs_values, name='get_abrs_values'),
#      path('set_test_mode/', views.set_test_mode, name='set_test_mode'),
# ]






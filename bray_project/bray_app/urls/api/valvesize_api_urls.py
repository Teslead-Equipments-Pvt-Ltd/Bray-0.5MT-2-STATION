from django.urls import path
from bray_app.views.api.valvesize_api_views import (
    valve_size_list, 
    get_all_valve_type, 
    get_enabled_category, 
    edit_valve_list,
    add_valve_size,
    update_valve_size,
    delete_valve_size,
    bulk_delete_valvesize_api
    
)


urlpatterns = [
    path('valvesize/',valve_size_list, name='valve_size_list'),
    path('valvesize/edit/<int:size_id>/',edit_valve_list, name='edit_valve_list'),
    path('valvesize/add/',add_valve_size, name='add_valve_size_new'),
    path('valvesize/update/<int:size_id>/',update_valve_size, name='update_valve_size'),
    path('valvesize/delete/<int:size_id>/',delete_valve_size, name="delete_valve_size"),
    path('valvesize/bulk_delete/',bulk_delete_valvesize_api, name="bulk_delete_valvesize"),
    path('get_valve_type/',get_all_valve_type, name='valve_type_list'),
    path('enabled_categories/',get_enabled_category, name='enabled_category_list'),

]
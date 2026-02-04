from django.urls import path
from bray_app.views.api.testmode_api_views import set_test_mode,check_incompletetest,delete_incomplete_test


urlpatterns = [
    path('set_test_mode/', set_test_mode, name='set_test_mode'),
    path('check_incomplete_test/', check_incompletetest, name='check_incomplete_test'),
    path('delete_incomplete_test/<int:stationNum>/<str:serialNo>/',delete_incomplete_test,name='delete_old_test'),
    
]
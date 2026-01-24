from django.urls import path
from bray_app.views.api.testmode_api_views import set_test_mode

urlpatterns = [
    path('set_test_mode/', set_test_mode, name='set_test_mode'),
]
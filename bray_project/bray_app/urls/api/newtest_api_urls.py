from django.urls import path
from bray_app.views.api.newtest_api_views import check_incompletetest

urlpatterns = [
    path('check_incomplete_test/', check_incompletetest, name='check_incomplete_test'),
]
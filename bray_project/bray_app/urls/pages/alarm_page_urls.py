from django.urls import path
from bray_app.views.pages.alarm_page_views import alarm_page

urlpatterns = [
    path("alarm/", alarm_page, name="alarm_page"),
]
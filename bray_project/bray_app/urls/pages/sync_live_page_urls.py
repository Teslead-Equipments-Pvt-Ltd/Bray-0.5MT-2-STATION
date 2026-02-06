from django.urls import path
from bray_app.views.pages.sync_live_page_views import sync_station_page

urlpatterns = [
    path("sync_page/", sync_station_page, name="sync_page"),
]

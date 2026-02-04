from django.urls import path
from bray_app.views.pages.instrument_type_page_views import instrument_type_page

urlpatterns = [
    path("instrument_type/", instrument_type_page, name="instrument_type"),
]

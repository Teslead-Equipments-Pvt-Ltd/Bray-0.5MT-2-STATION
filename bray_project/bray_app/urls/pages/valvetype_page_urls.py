from django.urls import path
from bray_app.views.pages.valvetype_page_views import valve_type_page

urlpatterns = [
    path("valve_type/", valve_type_page, name="valve_type"),
]

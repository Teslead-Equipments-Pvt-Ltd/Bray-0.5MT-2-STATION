from django.urls import path
from bray_app.views.pages.vtr_page_views import vtr_page

urlpatterns = [
    path("vtr/", vtr_page, name="vtr_page"),
]

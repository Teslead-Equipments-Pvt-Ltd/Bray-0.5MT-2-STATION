from django.urls import path
from bray_app.views.pages.valvesize_page_views import  valve_size


urlpatterns = [

    path("valvesize/", valve_size, name="valvesize")

]

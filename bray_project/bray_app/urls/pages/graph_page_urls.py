from django.urls import path
from bray_app.views.pages.graph_page_views import graph_page

urlpatterns = [
    path("graph/", graph_page, name="graph_page"),
]

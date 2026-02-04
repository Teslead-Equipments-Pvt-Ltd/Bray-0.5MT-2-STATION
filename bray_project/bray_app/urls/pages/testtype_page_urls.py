from django.urls import path
from bray_app.views.pages.testtype_page_views import testtype_page

urlpatterns = [
    path("testtype/", testtype_page, name="testtype"),
]

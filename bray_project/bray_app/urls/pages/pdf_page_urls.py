from django.urls import path
from bray_app.views.pages.pdf_page_views import pdf_page

urlpatterns = [
    path("pdf/", pdf_page, name="pdf_page"),
]

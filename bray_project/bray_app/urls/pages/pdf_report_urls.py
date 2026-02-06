from django.urls import path
from bray_app.views.pages.pdf_report_views import pdf_report

urlpatterns = [
    path("pdf_report/", pdf_report, name="pdf_report"),
]

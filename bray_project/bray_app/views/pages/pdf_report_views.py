from django.shortcuts import render
from bray_app.decorators import permission_required
from bray_app.services.pdf_service import get_abrs_value

@permission_required("Graph")
def pdf_report(request):
    get_abrs_value()
    return render(request, "pdf_report.html")
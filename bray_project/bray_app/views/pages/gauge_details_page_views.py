from django.shortcuts import render
from bray_app.decorators import permission_required


@permission_required("Gauge Details")
def gauge_details_page(request):
    """
    Render the gauge details page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "gauge_details.html")

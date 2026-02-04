from django.shortcuts import render
from bray_app.decorators import permission_required

@permission_required("vtr")
def vtr_page(request):
    """
    Render the gauge details page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "vtr.html")

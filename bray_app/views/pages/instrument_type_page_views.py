from django.shortcuts import render
from bray_app.decorators import permission_required


@permission_required("Instrument Type")
def instrument_type_page(request):
    """
    Render the instrument type page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "instrument_type.html")

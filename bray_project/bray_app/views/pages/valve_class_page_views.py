from django.shortcuts import render
from bray_app.decorators import permission_required


@permission_required("Valve Class")
def valve_class_page(request):
    """
    Render the valve class list page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "valve_class.html")

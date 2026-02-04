from django.shortcuts import render
from bray_app.decorators import permission_required

@permission_required("Standard")
def standard_list_page(request):
    """
    Render the standards list page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "standard_list.html")

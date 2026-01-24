from django.shortcuts import render
from bray_app.decorators import permission_required

@permission_required("Graph")
def graph_page(request):
    """
    Render the gauge details page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "graph.html")

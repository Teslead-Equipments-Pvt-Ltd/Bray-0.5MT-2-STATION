from django.shortcuts import render
from bray_app.decorators import permission_required

@permission_required("Configuration")
def configuration_page(request):
    return render(request, "config2.html")
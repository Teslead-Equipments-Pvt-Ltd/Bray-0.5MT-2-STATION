"""
ABRS Page Views - Render ABRS pages (page only, data via API)
"""
from django.shortcuts import render
from bray_app.decorators import login_required


@login_required
def abrs_page(request):
    """
    Render the ABRS Serial Updation page
    Data is loaded via API call from JavaScript
    """
    return render(request, 'abrs.html')

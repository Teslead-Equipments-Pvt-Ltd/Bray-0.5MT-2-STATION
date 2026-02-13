from django.shortcuts import render, redirect
from bray_app.decorators import login_required


@login_required
def employee_list_page(request):
    """
    Render the employee list page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, 'employee.html')


@login_required
def test_permissions_page(request):
    """
    Render a test page to verify permission sections are returned by API.
    This is a diagnostic page to help troubleshoot permission loading issues.
    """
    return render(request, 'test_permissions.html')

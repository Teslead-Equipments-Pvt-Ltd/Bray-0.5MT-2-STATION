from django.shortcuts import render, redirect
from bray_app.decorators import login_required


@login_required
def employee_list_page(request):
    """
    Render the employee list page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, 'employee.html')

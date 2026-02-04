from django.shortcuts import render
from bray_app.decorators import login_required


@login_required
def alarm_page(request):
    """Render the alarm management page."""
    return render(request, 'alarm.html')
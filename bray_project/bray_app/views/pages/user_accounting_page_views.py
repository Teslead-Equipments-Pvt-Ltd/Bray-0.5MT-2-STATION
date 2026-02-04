from django.shortcuts import render
from bray_app.decorators import login_required


@login_required
def user_accounting_page(request):
    """
    Render the user accounting page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, 'user_account.html')

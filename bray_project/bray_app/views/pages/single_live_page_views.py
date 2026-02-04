from django.shortcuts import render

def single_station_page(request):
    """
    Render the livepage.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "livepage.html")
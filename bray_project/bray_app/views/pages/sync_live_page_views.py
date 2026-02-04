from django.shortcuts import render



def sync_station_page(request):
    """
    Render the standards list page.
    Data will be fetched via API call from frontend JavaScript.
    """
    return render(request, "syncpage.html")
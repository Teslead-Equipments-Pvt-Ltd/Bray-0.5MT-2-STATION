from django.http import JsonResponse
from bray_app.services.form_service import get_status, get_station_data, compare_station_data
import traceback

def continue_station2(request):
    try:
        # Get status from service
        station1_status, station2_status, sync_status = get_status()

        # SYNC ONLY: Application now only works in sync mode, always redirect to sync_page
        redirect_url = "/sync_page"

        # Check if both stations are enabled and data matches
        if station1_status == "Enabled" and station2_status == "Enabled":
            # Get station data from service
            station1_data, station2_data = get_station_data()

            # Compare both sets of data using service
            if not compare_station_data(station1_data, station2_data):
                return JsonResponse({
                    "status": "failure",
                    "message": "Station 1 and Station 2 values do not match."
                })

        # NON-SYNC ONLY: Commented out since application only works in sync mode
        # if sync_status == 1:
        #     if station1_status == "Enabled" and station2_status == "Enabled":
        #         # Get station data from service
        #         station1_data, station2_data = get_station_data()
        #
        #         # Compare both sets of data using service
        #         if compare_station_data(station1_data, station2_data):
        #             redirect_url = "/sync_page"
        #            
        #         else:
        #             return JsonResponse({
        #                 "status": "failure",
        #                 "message": "Station 1 and Station 2 values do not match."
        #             })
        #
        #     elif station1_status == "Enabled" or station2_status == "Enabled":
        #         redirect_url = "/sync_page"
        #
        # else:
        #     redirect_url = "/single_page"

        # Final consistent return
        return JsonResponse({
            "status": "success",
            "redirect_url": redirect_url,
            "station1_status": station1_status,
            "station2_status": station2_status
        })

    except Exception as e:
        print("Error in continue_station2:", e)
        print(traceback.format_exc())
        return JsonResponse({
            "status": "failure",
            "message": f"Error: {str(e)}"
        })
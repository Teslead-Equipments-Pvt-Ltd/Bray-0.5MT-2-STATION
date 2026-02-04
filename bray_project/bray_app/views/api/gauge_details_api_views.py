from django.http import JsonResponse
from bray_app.decorators import permission_required
from bray_app.services.gauge_details_service import (
    get_all_gauges,
    get_instrument_types,
    get_next_instrument_id,
    insert_gauge,
    update_gauge,
    delete_gauge_record,
    check_duplicate_serial,
    count_enabled_gauges_by_station
)


@permission_required("Gauge Details")
def get_all_gauges_api(request):
    """
    GET endpoint to retrieve all gauges.
    Returns JSON array of gauges.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    rows = get_all_gauges()
    instrument_types = get_instrument_types()
    
    gauges_list = []
    for r in rows:
        cal_due_date = r[4]
        cal_done_date = r[5]
        
        gauges_list.append({
            "gauge_id": r[0],
            "gauge_ser_no": r[1],
            "range": r[2],
            "gauge_type": r[3],
            "cal_due_date": cal_due_date.strftime('%Y-%m-%d') if cal_due_date else '',
            "cal_done_date": cal_done_date.strftime('%Y-%m-%d') if cal_done_date else '',
            "active_status": r[6],
            "station_id": r[7],
            "due_alarm": r[8] if len(r) > 8 else None,
        })
    
    existing_serials = [g["gauge_ser_no"] for g in gauges_list if g["gauge_ser_no"]]
    
    # Get superuser level from session
    superuser_level = request.session.get("superuser", 0)
    
    return JsonResponse({
        "gauges": gauges_list,
        "instrument_types": instrument_types,
        "existing_serials": existing_serials,
        "superuser_level": superuser_level
    })


def _parse_date(date_str):
    if not date_str or date_str.strip() == '':
        return None
    try:
        from datetime import datetime
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except:
        return None


@permission_required("Gauge Details")
def add_gauge_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    serial = request.POST.get("serial", "").strip()
    range_val = request.POST.get("range", "").strip()
    gauge_type = request.POST.get("type", "").strip()
    cal_done_date = _parse_date(request.POST.get("done_date", ""))
    cal_due_date = _parse_date(request.POST.get("due_date", ""))
    station_id = request.POST.get("station_id", "").strip()
    status = request.POST.get("status", "").strip().lower()

    if not serial:
        return JsonResponse({"error": "Serial number is required"}, status=400)

    if not range_val:
        return JsonResponse({"error": "Range is required"}, status=400)

    if check_duplicate_serial(serial):
        return JsonResponse({"error": "Serial number already exists"}, status=400)

    try:
        station_id_int = int(station_id) if station_id else 0
    except:
        station_id_int = 0

    active_status = 1 if status == 'enable' else 0

    # Check station limit (max 10 enabled per station)
    if active_status == 1 and station_id_int > 0:
        count = count_enabled_gauges_by_station(station_id_int)
        if count >= 10:
            return JsonResponse({"error": f"Station {station_id_int} already has 10 enabled gauges"}, status=400)

    next_id = get_next_instrument_id()
    insert_gauge(next_id, serial, range_val, gauge_type, cal_due_date, cal_done_date, active_status, station_id_int)

    return JsonResponse({"success": True, "message": "Gauge added", "id": next_id})


@permission_required("Gauge Details")
def edit_gauge_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    serial = request.POST.get("serial", "").strip()
    range_val = request.POST.get("range", "").strip()
    gauge_type = request.POST.get("type", "").strip()
    cal_done_date = _parse_date(request.POST.get("done_date", ""))
    cal_due_date = _parse_date(request.POST.get("due_date", ""))
    station_id = request.POST.get("station_id", "").strip()
    status = request.POST.get("status", "").strip().lower()

    # Validation
    if not serial:
        return JsonResponse({"error": "Serial number is required"}, status=400)

    if not range_val:
        return JsonResponse({"error": "Range is required"}, status=400)

    # Check duplicate serial (excluding current record)
    if check_duplicate_serial(serial, pk):
        return JsonResponse({"error": "Serial number already exists"}, status=400)

    # Parse station_id
    try:
        station_id_int = int(station_id) if station_id else 0
    except:
        station_id_int = 0

    active_status = 1 if status == 'enable' else 0

    # Check station limit (max 10 enabled per station)
    if active_status == 1 and station_id_int > 0:
        count = count_enabled_gauges_by_station(station_id_int, pk)
        if count >= 10:
            return JsonResponse({"error": f"Station {station_id_int} already has 10 enabled gauges"}, status=400)

    update_gauge(pk, serial, range_val, gauge_type, cal_due_date, cal_done_date, active_status, station_id_int)

    return JsonResponse({"success": True, "message": "Gauge updated"})


@permission_required("Gauge Details")
def delete_gauge_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
    
    delete_gauge_record(pk)
    return JsonResponse({"success": True, "message": "Gauge deleted successfully"})


def check_serial_exists_api(request):
    """API to check if serial number exists (for real-time validation)"""
    serial = request.GET.get("serial", "").strip()
    exclude_id = request.GET.get("exclude_id", "").strip()
    
    if not serial:
        return JsonResponse({"exists": False})
    
    exclude_id_int = None
    if exclude_id:
        try:
            exclude_id_int = int(exclude_id)
        except:
            pass
    
    exists = check_duplicate_serial(serial, exclude_id_int)
    return JsonResponse({"exists": bool(exists)})


@permission_required("Gauge Details")
def save_gauges_api(request):
    """API to save all gauge rows (bulk save)"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        # Extract all rows from form
        gauge_names = request.POST.getlist('station1_gauge_name[]')
        serials = request.POST.getlist('station1_serial[]')
        ranges = request.POST.getlist('station1_range[]')
        types = request.POST.getlist('station1_type[]')
        done_dates = request.POST.getlist('station1_done_date[]')
        due_dates = request.POST.getlist('station1_due_date[]')
        station_ids = request.POST.getlist('station1_id[]')
        statuses = request.POST.getlist('station1_status[]')
        instrument_ids = request.POST.getlist('station1_instrument_id[]')

        # Validate duplicate serial numbers within form
        serial_map = {}
        for i in range(len(serials)):
            serial = serials[i].strip()
            if serial:
                instrument_id = ''
                try:
                    instrument_id = instrument_ids[i].strip()
                except (IndexError, ValueError):
                    pass
                
                if serial.lower() in serial_map:
                    return JsonResponse({"error": f'Duplicate serial number "{serial}" in form'}, status=400)
                serial_map[serial.lower()] = (i, instrument_id)

        # Validate against database
        for serial, (idx, current_id) in serial_map.items():
            exclude_id = int(current_id) if current_id else None
            if check_duplicate_serial(serial, exclude_id):
                return JsonResponse({"error": f'Serial number "{serial}" already exists in database'}, status=400)

        # Validate station counts
        station_counts = {}
        for i in range(len(serials)):
            station_id_str = station_ids[i].strip() if i < len(station_ids) else ''
            status_str = statuses[i].strip().lower() if i < len(statuses) else ''
            
            if station_id_str and status_str == 'enable':
                try:
                    station_id_int = int(station_id_str)
                    station_counts[station_id_int] = station_counts.get(station_id_int, 0) + 1
                except:
                    pass
        
        for station_id_int, count in station_counts.items():
            if count > 10:
                return JsonResponse({"error": f'Station {station_id_int} has {count} enabled rows. Max 10 allowed.'}, status=400)

        # Process each row
        for i in range(len(serials)):
            serial = serials[i].strip()
            range_val = ranges[i].strip() if i < len(ranges) else ''
            gauge_type = types[i].strip() if i < len(types) else ''
            cal_done_date = _parse_date(done_dates[i]) if i < len(done_dates) else None
            cal_due_date = _parse_date(due_dates[i]) if i < len(due_dates) else None
            
            try:
                station_id = int(station_ids[i]) if i < len(station_ids) and station_ids[i].strip() else 0
            except:
                station_id = 0

            active_status = 1 if (i < len(statuses) and statuses[i].strip().lower() == 'enable') else 0

            # Get or generate instrument ID
            try:
                gauge_id = int(instrument_ids[i]) if i < len(instrument_ids) and instrument_ids[i].strip() else None
            except:
                gauge_id = None

            # Skip empty rows
            if not serial and not range_val and not gauge_type and not station_id:
                continue

            if gauge_id:
                # Update existing
                update_gauge(gauge_id, serial, range_val, gauge_type, cal_due_date, cal_done_date, active_status, station_id)
            else:
                # Insert new
                if serial or range_val or gauge_type or station_id:
                    next_id = get_next_instrument_id()
                    insert_gauge(next_id, serial, range_val, gauge_type, cal_due_date, cal_done_date, active_status, station_id)

        return JsonResponse({"success": True, "message": "Gauge details saved successfully"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

"""
ABRS API Views - Handle JSON API requests for ABRS operations
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from bray_app.services.abrs_service import ABRSService


def _get_json_data(request):
    """Helper to parse JSON from request body"""
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


@require_http_methods(["GET"])
def api_get_abrs_table_data(request):
    """
    API endpoint to get ABRS table data for rendering
    GET /api/abrs/table-data/
    """
    try:
        result = ABRSService.get_table_data()
        return JsonResponse({
            'status': 'success',
            'column_headers': result['column_headers'],
            'data': result['data']
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error fetching ABRS data: {str(e)}',
            'column_headers': [],
            'data': []
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_import_by_date(request):
    """
    API endpoint to sync ABRS data by date range
    POST /api/abrs/import-by-date/
    """
    try:
        data = _get_json_data(request)
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if not from_date or not to_date:
            return JsonResponse({
                'status': 'error',
                'message': 'Both from_date and to_date are required'
            }, status=400)
        
        result = ABRSService.sync_serials_by_date_range(from_date, to_date)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'imported_count': result['imported_count'],
                'skipped_count': result['skipped_count'],
                'total_scanned': result['total_scanned'],
                'serials': result['serials'],
                'skipped_serials': result.get('skipped_serials', [])
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_import_by_serial(request):
    """
    API endpoint to import serial from ABRS database
    POST /api/abrs/import-by-serial/
    """
    try:
        data = _get_json_data(request)
        serial_number = data.get('serial_number')
        
        if not serial_number:
            return JsonResponse({
                'status': 'error',
                'message': 'Serial number is required'
            }, status=400)
        
        # Import serial from ABRS database
        result = ABRSService.import_serial_from_abrs(serial_number)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'serial_no': result.get('serial_no'),
                'assembly_no': result.get('assembly_no')
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def api_search_serials(request):
    """
    API endpoint to search for serial numbers (autocomplete)
    GET /api/abrs/search-serials/?q=ABC
    """
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 1:
            return JsonResponse({'status': 'success', 'serials': []})
        
        serials = ABRSService.search_serials(query)
        return JsonResponse({'status': 'success', 'serials': serials})
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}',
            'serials': []
        }, status=500)


@require_http_methods(["GET"])
def api_serial_details(request, serial_number):
    """
    API endpoint to get details for a specific serial number
    GET /api/abrs/serial-details/<serial_number>/
    """
    try:
        details = ABRSService.get_serial_details(serial_number)
        
        if details:
            return JsonResponse({'status': 'success', 'data': details})
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Serial number not found'
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_sync_by_single_date(request):
    """
    API endpoint to sync ABRS data by single date
    POST /api/abrs/sync-by-date/
    """
    try:
        data = _get_json_data(request)
        date = data.get('date')
        
        if not date:
            return JsonResponse({
                'status': 'error',
                'message': 'Date is required'
            }, status=400)
        
        result = ABRSService.sync_serials_by_date(date)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'updated_count': result['updated_count'],
                'total_scanned': result['total_scanned'],
                'serials': result['serials']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_status(request):
    """
    API endpoint to update status of a serial number
    POST /api/abrs/update-status/
    Body: {
        "serial_no": "ABC123",
        "status_code": 2
    }
    Status codes:
        0 = Not Performed
        1 = Running
        2 = Test Performed
        3 = Test Performed & Pushed
    """
    try:
        data = _get_json_data(request)
        serial_no = data.get('serial_no')
        status_code = data.get('status_code')
        
        if not serial_no:
            return JsonResponse({
                'status': 'error',
                'message': 'Serial number is required'
            }, status=400)
        
        if status_code is None:
            return JsonResponse({
                'status': 'error',
                'message': 'Status code is required'
            }, status=400)
        
        try:
            status_code = int(status_code)
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Status code must be an integer (0-3)'
            }, status=400)
        
        result = ABRSService.update_status(serial_no, status_code)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'serial_no': result['serial_no'],
                'status_code': result['status_code'],
                'status_text': result['status_text']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_get_assembly(request):
    """
    API endpoint to get assembly ID from ABRS database and update local database
    POST /api/abrs/get-assembly/
    Body: {
        "serial_no": "ABC123"
    }
    """
    try:
        data = _get_json_data(request)
        serial_no = data.get('serial_no')
        
        if not serial_no:
            return JsonResponse({
                'status': 'error',
                'message': 'Serial number is required'
            }, status=400)
        
        result = ABRSService.get_assembly_from_abrs(serial_no)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'success': True,
                'message': result['message'],
                'serial_no': result['serial_no'],
                'assembly_no': result['assembly_no']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'success': False,
                'message': result['message']
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_push_data(request):
    """
    API endpoint to push test data from local database to ABRS database
    POST /api/abrs/push-data/
    Body: {
        "serial_no": "ABC123",
        "assembly_no": "12345"
    }
    
    This endpoint reads 13 column values from local database and pushes them
    to ABRS database using separate queries for each test parameter.
    """
    try:
        data = _get_json_data(request)
        serial_no = data.get('serial_no')
        assembly_no = data.get('assembly_no')
        
        if not serial_no:
            return JsonResponse({
                'status': 'error',
                'message': 'Serial number is required'
            }, status=400)
        
        if not assembly_no:
            return JsonResponse({
                'status': 'error',
                'message': 'Assembly number is required'
            }, status=400)
        
        print(f"Push request: Serial={serial_no}, Assembly={assembly_no}")
        
        # Push data to ABRS database
        result = ABRSService.push_data_to_abrs(serial_no, assembly_no)
        
        print(f"Push result: {result}")
        
        if result['success']:
            # Update status to 3 (Test Performed & Pushed) after successful push
            status_result = ABRSService.update_status(serial_no, 3)
            
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'success_count': result.get('success_count', 0),
                'serial_no': serial_no,
                'assembly_no': assembly_no
            })
        else:
            # Return detailed error information
            return JsonResponse({
                'status': 'error',
                'message': result['message'],
                'success_count': result.get('success_count', 0),
                'failed_tests': result.get('failed_tests', [])
            }, status=400)
            
    except Exception as e:
        import traceback
        print(f"Push error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)

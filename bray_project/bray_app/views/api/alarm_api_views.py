from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bray_app.decorators import login_required
from bray_app.services.alarm_service import (
    get_all_alarms,
    get_alarm_by_id,
    create_alarm,
    update_alarm,
    delete_alarm,
    check_alarm_code_exists,
    get_existing_alarm_codes
)
import json


@login_required
@require_http_methods(["GET"])
def alarm_list_api(request):
    """API endpoint to get all alarms."""
    try:
        alarms = get_all_alarms()
        existing_codes = get_existing_alarm_codes()
        
        return JsonResponse({
            'success': True,
            'alarms': alarms,
            'existing_codes': existing_codes
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def alarm_add_api(request):
    """API endpoint to add a new alarm."""
    try:
        alarm_code = request.POST.get('alarm_code', '').strip()
        alarm_name = request.POST.get('alarm_name', '').strip()
        
        # Validation
        if not alarm_code:
            return JsonResponse({
                'success': False,
                'error': 'Alarm code is required'
            })
            
        if not alarm_name:
            return JsonResponse({
                'success': False,
                'error': 'Alarm name is required'
            })
        
        # Check if code already exists
        if check_alarm_code_exists(alarm_code):
            return JsonResponse({
                'success': False,
                'error': 'Alarm code already exists'
            })
        
        # Create alarm
        alarm_id = create_alarm(alarm_code, alarm_name)
        
        return JsonResponse({
            'success': True,
            'message': 'Alarm added successfully',
            'alarm_id': alarm_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def alarm_edit_api(request, alarm_id):
    """API endpoint to edit an existing alarm."""
    try:
        # Get alarm data
        alarm = get_alarm_by_id(alarm_id)
        if not alarm:
            return JsonResponse({
                'success': False,
                'error': 'Alarm not found'
            })
        
        alarm_code = request.POST.get('alarm_code', '').strip()
        alarm_name = request.POST.get('alarm_name', '').strip()
        
        # Validation
        if not alarm_code:
            return JsonResponse({
                'success': False,
                'error': 'Alarm code is required'
            })
            
        if not alarm_name:
            return JsonResponse({
                'success': False,
                'error': 'Alarm name is required'
            })
        
        # Check if code already exists (excluding current alarm)
        if check_alarm_code_exists(alarm_code, alarm_id):
            return JsonResponse({
                'success': False,
                'error': 'Alarm code already exists'
            })
        
        # Update alarm
        success = update_alarm(alarm_id, alarm_code, alarm_name)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Alarm updated successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to update alarm'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def alarm_delete_api(request, alarm_id):
    """API endpoint to delete an alarm."""
    try:
        # Check if alarm exists
        alarm = get_alarm_by_id(alarm_id)
        if not alarm:
            return JsonResponse({
                'success': False,
                'error': 'Alarm not found'
            })
        
        # Delete alarm
        success = delete_alarm(alarm_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Alarm deleted successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete alarm'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def alarm_detail_api(request, alarm_id):
    """API endpoint to get alarm details."""
    try:
        alarm = get_alarm_by_id(alarm_id)
        if not alarm:
            return JsonResponse({
                'success': False,
                'error': 'Alarm not found'
            })
        
        return JsonResponse({
            'success': True,
            'alarm': alarm
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
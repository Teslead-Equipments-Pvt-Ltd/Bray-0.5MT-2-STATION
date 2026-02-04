"""
Valve Serial API Views - Handle valve serial number validation and assembly ID operations
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from bray_app.decorators import permission_required
from bray_app.services.valve_serial_service import ValveSerialService


@csrf_exempt
def check_assembly_id(request):
    """
    Enhanced valve serial number validation with status checking
    - Check if serial exists in database
    - If exists, check status field (0=in progress, 2/3=completed, need deletion)
    - If status=0, check assembly ID availability
    - Check ABRS server connection for button visibility
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method allowed"})
    
    try:
        data = json.loads(request.body)
        serial_number = data.get('serial_number', '').strip()
        
        if not serial_number:
            return JsonResponse({"status": "error", "message": "Serial number is required"})
        
        # Step 1: Check if serial number exists in database
        serial_exists = ValveSerialService.check_serial_exists(serial_number)
        
        if not serial_exists:
            # Serial number doesn't exist - check ABRS server connection for new entry
            abrs_connected = ValveSerialService.check_abrs_connection()
            
            return JsonResponse({
                "status": "success",
                "serial_exists": False,
                "abrs_connected": abrs_connected,
                "action": "show_buttons"
            })
        
        # Step 2: Serial exists, now check status
        status = ValveSerialService.get_serial_status(serial_number)
        
        # If status is 2 or 3 (completed), ask for deletion
        if status in [2, 3]:
            return JsonResponse({
                "status": "success",
                "serial_exists": True,
                "status_value": status,
                "action": "ask_deletion",
                "message": f"Serial number {serial_number} has completed testing (status: {status}). Do you want to delete it for retesting?"
            })
        
        # Step 3: Status is 0 (in progress), check assembly ID
        elif status == 0:
            assembly_no = ValveSerialService.get_assembly_number(serial_number)
            
            if assembly_no:
                # Assembly ID exists - show green tick, hide buttons
                return JsonResponse({
                    "status": "success",
                    "serial_exists": True,
                    "status_value": status,
                    "assembly_exists": True,
                    "assembly_id": assembly_no,  # Changed from assembly_no to assembly_id
                    "action": "show_tick"
                })
            else:
                # Assembly ID doesn't exist - check ABRS server connection
                abrs_connected = ValveSerialService.check_abrs_connection()
                
                return JsonResponse({
                    "status": "success",
                    "serial_exists": True,
                    "status_value": status,
                    "assembly_exists": False,
                    "abrs_connected": abrs_connected,
                    "action": "show_buttons"
                })
        else:
            # Other status values - check ABRS server connection
            abrs_connected = ValveSerialService.check_abrs_connection()
            return JsonResponse({
                "status": "success",
                "serial_exists": True,
                "status_value": status,
                "abrs_connected": abrs_connected,
                "action": "show_buttons"
            })
                
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Database error: {str(e)}"})


@csrf_exempt
def get_assembly_id(request):
    """
    Get assembly ID from ABRSSample database (display only, no database saving)
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method allowed"})
    
    try:
        data = json.loads(request.body)
        serial_number = data.get('serial_number', '').strip()
        
        if not serial_number:
            return JsonResponse({"status": "error", "message": "Serial number is required"})
        
        # Get assembly ID from ABRS database
        assembly_id, error_message = ValveSerialService.get_assembly_id_from_abrs(serial_number)
        
        if error_message:
            return JsonResponse({
                "status": "error", 
                "message": error_message
            })
        
        return JsonResponse({
            "status": "success", 
            "message": "Assembly ID retrieved successfully",
            "assembly_id": assembly_id
        })
            
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON data"})
    except Exception as e:
        print(f"Error in get_assembly_id: {str(e)}")  # For debugging
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"})


@csrf_exempt
def delete_and_retest_serial(request):
    """
    Delete existing serial number from abrs_result_status table for retesting
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method allowed"})
    
    try:
        data = json.loads(request.body)
        serial_number = data.get('serial_number', '').strip()
        
        if not serial_number:
            return JsonResponse({"status": "error", "message": "Serial number is required"})
        
        # Get assembly ID before updating status
        assembly_id = ValveSerialService.get_assembly_number(serial_number)
        
        # Update status to 0 (previously had delete function but logic changed)
        rows_updated = ValveSerialService.delete_serial(serial_number)
        
        if rows_updated > 0:
            return JsonResponse({
                "status": "success", 
                "success": True,
                "message": f"Serial number {serial_number} updated successfully. You can now retest.",
                "assembly_id": assembly_id  # Return assembly ID if it exists
            })
        else:
            return JsonResponse({
                "status": "error", 
                "success": False,
                "message": "Serial number not found in database"
            })
            
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "success": False, "message": "Invalid JSON data"})
    except Exception as e:
        print(f"Error in delete_and_retest_serial: {str(e)}")
        return JsonResponse({"status": "error", "success": False, "message": f"Unexpected error: {str(e)}"})


@csrf_exempt
def save_to_local_db(request):
    """
    Get assembly ID from ABRS database and save both serial number and assembly ID to local database
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method allowed"})
    
    try:
        data = json.loads(request.body)
        serial_number = data.get('serial_number', '').strip()
        
        if not serial_number:
            return JsonResponse({"status": "error", "message": "Serial number is required"})
        
        # Check if record already exists first
        if ValveSerialService.check_serial_exists(serial_number):
            return JsonResponse({
                "status": "duplicate", 
                "message": f"Serial number {serial_number} already exists in the database. Do you want to delete it and retest?",
                "serial_number": serial_number
            })
        
        # Get assembly ID from ABRSSample database
        assembly_id, error_message = ValveSerialService.get_assembly_id_from_abrs(serial_number)
        abrs_connection_failed = error_message and "connection error" in error_message.lower()
        
        # Insert new record with assembly ID if found
        ValveSerialService.insert_serial_with_assembly(serial_number, assembly_id)
        
        if assembly_id:
            message = f"Serial number and assembly ID saved successfully: {assembly_id}"
        else:
            if abrs_connection_failed:
                message = "Serial number saved (ABRS not available)"
            else:
                message = "Serial number saved (Assembly ID not found in ABRS database)"
        
        return JsonResponse({
            "status": "success", 
            "message": message,
            "assembly_id": assembly_id
        })
            
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON data"})
    except Exception as e:
        print(f"Error in save_to_local_db: {str(e)}")  # For debugging
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"})


@csrf_exempt
def fetch_and_save_assembly(request):
    """
    Combined function: Fetch assembly ID from ABRS and save/update local DB record
    Works for both cases:
    1. Serial exists in local DB with status=0 but no assembly ID (UPDATE)
    2. Serial doesn't exist in local DB (INSERT)
    If ABRS fetch fails or serial not found in ABRS, still save the serial number without assembly ID
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST mevvvthod allowed"})
    
    try:
        data = json.loads(request.body)
        serial_number = data.get('serial_number', '').strip()
        
        if not serial_number:
            return JsonResponse({"status": "error", "message": "Serial number is required"})
        
        print(f"fetch_and_save_assembly called for serial: {serial_number}")
        
        # Check if record exists in local DB
        record_exists, record_id, status = ValveSerialService.check_serial_exists_by_id(serial_number)
        
        if record_exists:
            print(f"Record exists with status: {status}")
            
            # If status is not 0, don't allow update
            if status != 0:
                return JsonResponse({
                    "status": "error", 
                    "message": f"Serial number has status {status}, cannot update"
                })
        else:
            print(f"Record does not exist, will create new")
        
        # Try to fetch assembly ID from ABRS database
        print(f"Attempting to connect to ABRS database...")
        assembly_id, error_message = ValveSerialService.get_assembly_id_from_abrs(serial_number)
        abrs_fetch_success = assembly_id is not None
        abrs_connection_failed = error_message and "connection error" in error_message.lower()
        
        if assembly_id:
            print(f"Assembly ID found: {assembly_id}")
        elif error_message:
            print(f"ABRS error: {error_message}")
        
        # Save or update the local record - with or without assembly ID
        if record_exists:
            # UPDATE existing record
            if assembly_id:
                ValveSerialService.update_assembly_number(serial_number, assembly_id)
                message = f"Assembly ID fetched and saved successfully"
                print(f"Updated record with assembly ID: {assembly_id}")
            else:
                # Record already exists, no assembly ID found
                if abrs_connection_failed:
                    message = f"Serial number already saved (ABRS not available)"
                else:
                    message = f"Serial number already saved (Assembly ID not found in ABRS database)"
                print(f"Record exists but no assembly ID found")
        else:
            # INSERT new record
            ValveSerialService.insert_serial_with_assembly(serial_number, assembly_id)
            
            if assembly_id:
                message = f"Serial number and assembly ID saved successfully"
                print(f"Inserted new record with assembly ID: {assembly_id}")
            else:
                if abrs_connection_failed:
                    message = f"Serial number saved successfully (ABRS not available)"
                else:
                    message = f"Serial number saved successfully (Assembly ID not found in ABRS database)"
                print(f"Inserted new record without assembly ID")
        
        print(f"Operation completed successfully")
        return JsonResponse({
            "status": "success", 
            "message": message,
            "assembly_id": assembly_id,
            "abrs_fetch_success": abrs_fetch_success
        })
            
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return JsonResponse({"status": "error", "message": "Invalid JSON data"})
    except Exception as e:
        print(f"Error in fetch_and_save_assembly: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"})
# Enhanced Valve Serial Number Validation

## Overview
Implemented enhanced valve serial number validation logic that checks serial number availability, status, assembly ID existence, and ABRS server connectivity to determine which buttons to show.

## Validation Flow

### 1. Serial Number Entry
When a user enters a valve serial number, the system automatically validates it with the following logic:

### 2. Check Serial Number Existence (Step 1)
- Query `abrs_result_status` table to check if `SERIAL_NO` exists
- If not found → proceed to step 6 (new serial number)
- If found → proceed to step 3

### 3. Check Status Field (Step 2)
- Query `STATUS` field for the existing serial number
- **Status = 2 or 3 (Completed)**: Proceed to step 7 (deletion flow)
- **Status = 0 (In Progress)**: Proceed to step 4 (assembly ID check)
- **Other status values**: Proceed to step 6 (ABRS connectivity check)

### 4. Assembly ID Check (Step 3 - Status = 0 only)
- Query `ASSEMBLY_NO` field for the serial number
- Check if assembly ID exists and is not empty
- If assembly ID exists:
  - Show green tick ✓
  - Hide both "Get Assembly ID" and "Save in Local DB" buttons
- If assembly ID doesn't exist:
  - Proceed to step 6 (ABRS server connectivity check)

### 5. ABRS Server Connectivity Check (Step 4)
- Test connection to ABRS database
- **If connected**: Show both "Get Assembly ID" and "Save in Local DB" buttons
- **If not connected**: Show only "Save in Local DB" button (hide "Get Assembly ID")

### 6. New Serial Number Flow
- Serial number doesn't exist in database
- Check ABRS server connectivity and show appropriate buttons

### 7. Deletion Flow (Status 2/3)
- Show confirmation dialog asking if user wants to delete for retesting
- If confirmed: Delete record and restart validation process from step 1
- If cancelled: Clear input field and hide all buttons

## Implementation Details

### Backend Changes (valve_serial_api_views.py)

#### Enhanced `check_assembly_id()` function:
- Queries both `ASSEMBLY_NO` and `status` fields
- Implements status-based logic
- Checks ABRS server connectivity
- Returns structured response with action type

#### New `check_abrs_connection()` function:
- Tests ABRS database connectivity
- Returns boolean status

#### Updated `delete_and_retest_serial()` function:
- Handles deletion of completed test records
- Enables retesting workflow

### Frontend Changes (form.html)

#### Enhanced `checkAssemblyId()` function:
- Calls new API endpoint
- Handles structured response

#### New `handleSerialValidationResponse()` function:
- Processes API response based on action type
- Shows appropriate UI elements

#### New `deleteAndRetestSerial()` function:
- Handles deletion confirmation and API call
- Restarts validation after successful deletion

### URL Configuration
Added new endpoints to `form_api_urls.py`:
- `/api/newform/delete_and_retest_serial/`
- `/api/newform/save_to_local_db/`

## Button Visibility Logic

| Condition | Green Tick | Get Assembly ID | Save in Local DB |
|-----------|------------|-----------------|------------------|
| New serial number + ABRS connected | Hidden | Visible | Visible |
| New serial number + ABRS disconnected | Hidden | Hidden | Visible |
| Status=0 + Assembly exists | Visible | Hidden | Hidden |
| Status=0 + No assembly + ABRS connected | Hidden | Visible | Visible |
| Status=0 + No assembly + ABRS disconnected | Hidden | Hidden | Visible |
| Status=2/3 (Completed) | Hidden | Hidden | Hidden (Show deletion dialog) |

## Database Schema
The `abrs_result_status` table includes:
- `SERIAL_NO` - Valve serial number
- `ASSEMBLY_NO` - Assembly ID from ABRS database
- `status` - Test status (0=in progress, 2/3=completed)
- Other columns for test results

## Error Handling
- Database connection errors are handled gracefully
- ABRS server connectivity issues don't block local operations
- User-friendly error messages via SweetAlert2
- Proper button state management during API calls

## User Experience
- Real-time validation as user types (debounced)
- Clear visual feedback with green tick for completed validations
- Confirmation dialogs for destructive operations
- Loading states for all async operations
- Contextual button visibility based on system state
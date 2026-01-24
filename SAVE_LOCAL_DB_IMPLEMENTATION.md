# Save in Local DB Button Implementation

## Overview
Modified the valve serial number functionality to separate concerns:
- **"Get Assembly ID" button** - Only retrieves and displays assembly ID from ABRS database (no saving)
- **"Save in Local DB" button** - Retrieves assembly ID from ABRS and saves both serial number and assembly ID to local database

## Changes Made

### 1. Frontend Changes (form.html)
- Added "Save in Local DB" button for both Station 1 and Station 2
- Modified `getAssemblyId(station)` function to only display assembly ID (no green tick)
- Modified `saveToLocalDB(station)` function to save to database and show green tick
- Added helper functions `showSaveLocalDBButton()`, `hideSaveLocalDBButton()`, and `hideGetAssemblyButton()`
- Modified existing functions to show/hide buttons appropriately

### 2. CSS Changes (stationnew.css)
- Added styling for `.save-local-db-btn` class
- Green gradient background to distinguish from the blue "Get Assembly ID" button
- Hover and active states for better user experience
- Disabled state styling

### 3. Backend Changes (valve_serial_api_views.py)
- **Modified `get_assembly_id(request)`** - Removed database saving logic, only retrieves and returns assembly ID
- **Modified `save_to_local_db(request)`** - Now retrieves assembly ID from ABRS database first, then saves both serial number and assembly ID to local database
- Handles cases where assembly ID is not found in ABRS (saves only serial number)
- Returns assembly ID in response for display purposes

### 4. URL Configuration (form_api_urls.py)
- Added URL pattern for the new API endpoint: `/api/newform/save_to_local_db/`

## How It Works

1. **User enters valve serial number** - The system automatically checks if an assembly ID exists in local database
2. **If no assembly ID exists locally** - Both "Get Assembly ID" and "Save in Local DB" buttons are shown
3. **User clicks "Get Assembly ID"** - Retrieves and displays assembly ID from ABRS database (no saving)
4. **User clicks "Save in Local DB"** - Retrieves assembly ID from ABRS database and saves both serial number and assembly ID to local database
5. **Success feedback** - Green tick is shown and both buttons are hidden
6. **Error handling** - Appropriate error messages are displayed if something goes wrong

## Database Impact
- **"Get Assembly ID"** - No database changes, only displays information
- **"Save in Local DB"** - Inserts/updates records in `abrs_result_status` table with both `SERIAL_NO` and `ASSEMBLY_NO` fields
- If assembly ID is not found in ABRS, only `SERIAL_NO` is saved
- Existing records are updated with assembly ID if found

## User Experience
- Clear separation of concerns between viewing and saving
- "Get Assembly ID" shows information without commitment
- "Save in Local DB" performs the actual database operation
- Loading states during API calls
- Success/error feedback via SweetAlert popups
- Green tick appears only after successful save
- Works for both Station 1 and Station 2

## API Endpoint Details

### Get Assembly ID (Display Only)
**URL:** `/api/newform/get_assembly_id/`
**Method:** POST
**Payload:**
```json
{
    "serial_number": "string"
}
```

**Response (Success):**
```json
{
    "status": "success",
    "message": "Assembly ID retrieved successfully",
    "assembly_id": "string"
}
```

### Save to Local DB
**URL:** `/api/newform/save_to_local_db/`
**Method:** POST
**Payload:**
```json
{
    "serial_number": "string"
}
```

**Response (Success with Assembly ID):**
```json
{
    "status": "success",
    "message": "Serial number and assembly ID saved successfully: ASSEMBLY123",
    "assembly_id": "ASSEMBLY123"
}
```

**Response (Success without Assembly ID):**
```json
{
    "status": "success",
    "message": "Serial number saved (assembly ID not found in ABRS database)",
    "assembly_id": null
}
```

**Response (Error):**
```json
{
    "status": "error",
    "message": "Error description"
}
```
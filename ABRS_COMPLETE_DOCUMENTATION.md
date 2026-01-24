# ABRS Push Data - Complete Documentation

## Overview
Complete documentation for ABRS Push Data feature including frontend, backend, API, and database integration.

## System Architecture

```
Frontend (abrs.html)
    ↓ User clicks Push button
    ↓ JavaScript: pushToAbrs(serialNo, assemblyNo)
    ↓ AJAX POST Request
API Layer (abrs_api_views.py)
    ↓ api_push_data(request)
    ↓ Validates parameters
Service Layer (abrs_service.py)
    ↓ push_data_to_abrs(serial_no, assembly_no)
    ↓ get_abrs_connection()
Database Operations
    ↓ Read from Local DB (abrs_result_status)
    ↓ Update ABRS DB (abrsAssemblyTest)
    ↓ Update Status in Local DB
Response
    ↓ Success/Error JSON
    ↓ Frontend shows notification
    ↓ Table refreshes
```

## Database Structure

### Local Database: `abrs_result_status`
```sql
Columns:
- SERIAL_NO (VARCHAR)
- ASSEMBLY_NO (VARCHAR)
- STATUS (INT)
- COL1_VALUE to COL13_VALUE (VARCHAR)
```

### ABRS Database: `abrsAssemblyTest`
```sql
Columns:
- assemblyId (VARCHAR)
- testDetailId (INT)
- testValue (VARCHAR)
- updatedBy (VARCHAR)
- updatedDate (DATETIME)
```

## Files Structure

### 1. Frontend
**File:** `bray_app/templates/abrs.html`

### 2. Backend Service
**File:** `bray_app/services/abrs_service.py`

### 3. API Views
**File:** `bray_app/views/api/abrs_api_views.py`

### 4. URL Configuration
**File:** `bray_app/urls/api/abrs_api_urls.py`

## Frontend Implementation (abrs.html)

### Push Button HTML
```html
<button class="btn-action" onclick="pushToAbrs('${row.serial_no}', '${row.assembly_no}')" 
        style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
  <i class="fas fa-upload"></i> Push
</button>
```

### JavaScript Function: pushToAbrs()
```javascript
window.pushToAbrs = async function(serialNo, assemblyNo) {
  // Step 1: Show confirmation dialog
  const result = await Swal.fire({
    title: 'Push Data to ABRS?',
    html: `
      <div style="text-align: left; margin-top: 20px;">
        <p><strong>Serial Number:</strong> ${serialNo}</p>
        <p><strong>Assembly Number:</strong> ${assemblyNo}</p>
        <p class="text-muted mt-3">This will push test values to ABRS database</p>
      </div>
    `,
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#10b981',
    cancelButtonColor: '#6b7280',
    confirmButtonText: '<i class="fas fa-upload me-2"></i>Yes, Push',
    cancelButtonText: 'Cancel'
  });
  
  if (result.isConfirmed) {
    // Step 2: Show loading spinner
    Swal.fire({
      title: 'Pushing Data...',
      html: `
        <div style="text-align: left;">
          <p>Serial: <strong>${serialNo}</strong></p>
          <p>Assembly: <strong>${assemblyNo}</strong></p>
          <p class="text-muted mt-2">Pushing test data to ABRS database...</p>
        </div>
      `,
      allowOutsideClick: false,
      didOpen: () => { Swal.showLoading(); }
    });
    
    try {
      // Step 3: Make API call
      const response = await fetch('/api/abrs/push-data/', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'X-CSRFToken': getCsrfToken() 
        },
        body: JSON.stringify({ 
          serial_no: serialNo, 
          assembly_no: assemblyNo 
        })
      });
      
      const data = await response.json();
      
      if (response.ok && data.status === 'success') {
        // Step 4: Show success message
        Swal.fire({
          icon: 'success',
          title: 'Data Pushed Successfully!',
          html: `
            <div style="text-align: left; margin-top: 20px;">
              <p><strong>Serial:</strong> ${serialNo}</p>
              <p><strong>Assembly:</strong> ${assemblyNo}</p>
              <p class="text-success mt-3">Test values pushed to ABRS</p>
            </div>
          `,
          confirmButtonColor: '#10b981',
          timer: 3000
        });
        
        // Step 5: Refresh table
        loadTableData();
      } else {
        throw new Error(data.message || 'Failed to push data to ABRS');
      }
    } catch (error) {
      // Step 6: Show error message
      Swal.fire({
        icon: 'error',
        title: 'Push Failed',
        text: error.message || 'Failed to push data to ABRS',
        confirmButtonColor: '#ef4444'
      });
    }
  }
};
```

### Helper Function: getCsrfToken()
```javascript
function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}
```

## Backend Service Layer (abrs_service.py)

### Connection Function
```python
def get_abrs_connection():
    """Get ABRS database connection"""
    abrs_conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost;'
        'DATABASE=ABRSSample;'
        'Trusted_Connection=yes;'
        'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(abrs_conn_str)
```

### Main Push Function
```python
@staticmethod
def push_data_to_abrs(serial_no, assembly_no):
    """
    Push test data from local database to ABRS database.
    Updates existing rows only (no INSERT).
    
    Args:
        serial_no: Serial number
        assembly_no: Assembly number
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Step 1: Get test data from local database
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT SERIAL_NO, ASSEMBLY_NO, STATUS,
                       COL1_VALUE, COL2_VALUE, COL3_VALUE, COL4_VALUE, COL5_VALUE,
                       COL6_VALUE, COL7_VALUE, COL8_VALUE, COL9_VALUE, COL10_VALUE,
                       COL11_VALUE, COL12_VALUE, COL13_VALUE
                FROM abrs_result_status
                WHERE SERIAL_NO = %s AND ASSEMBLY_NO = %s
            """, [serial_no, assembly_no])
            
            row = cursor.fetchone()
            
            if not row:
                return {
                    'success': False,
                    'message': f'Serial {serial_no} not found in local database'
                }
            
            # Extract column values
            test_values = {
                'col1': row[3],   # Open Torque - Test ID 9
                'col2': row[4],   # Close Torque - Test ID 7
                'col3': row[5],   # Valve Cycle Test - Test ID 2
                'col4': row[6],   # Hydro Shell Test Result - Test ID 11
                'col5': row[7],   # Hydro Shell Test Duration - Test ID 12
                'col6': row[8],   # Hydro Seat P Test Result - Test ID 35
                'col7': row[9],   # Hydro Seat P Test Duration - Test ID 36
                'col8': row[10],  # Hydro Seat N Test Result - Test ID 31
                'col9': row[11],  # Hydro Seat N Test Duration - Test ID 32
                'col10': row[12], # Air Seat P Test Result - Test ID 19
                'col11': row[13], # Air Seat P Test Duration - Test ID 20
                'col12': row[14], # Air Seat N Test Result - Test ID 15
                'col13': row[15], # Air Seat N Test Duration - Test ID 16
            }
        
        # Step 2: Test ID mapping
        test_id_mapping = {
            'col1': 9,   'col2': 7,   'col3': 2,   'col4': 11,
            'col5': 12,  'col6': 35,  'col7': 36,  'col8': 31,
            'col9': 32,  'col10': 19, 'col11': 20, 'col12': 15,
            'col13': 16
        }
        
        # Step 3: Connect to ABRS database
        abrs_conn = get_abrs_connection()
        abrs_cursor = abrs_conn.cursor()
        
        # Step 4: Update each test parameter
        success_count = 0
        failed_tests = []
        skipped_count = 0
        
        for col_key, test_id in test_id_mapping.items():
            test_value = test_values.get(col_key)
            
            # Skip if value is empty
            if test_value is None or test_value == '' or test_value == '-':
                skipped_count += 1
                continue
            
            try:
                # Check if record exists
                abrs_cursor.execute("""
                    SELECT COUNT(*) FROM abrsAssemblyTest 
                    WHERE assemblyId = ? AND testDetailId = ?
                """, [assembly_no, test_id])
                
                exists = abrs_cursor.fetchone()[0] > 0
                
                if exists:
                    # Update existing record only
                    abrs_cursor.execute("""
                        UPDATE abrsAssemblyTest 
                        SET testValue = ?, updatedBy = 'Teslead-100MT', updatedDate = GETDATE()
                        WHERE assemblyId = ? AND testDetailId = ?
                    """, [test_value, assembly_no, test_id])
                    success_count += 1
                else:
                    # Skip if row doesn't exist
                    skipped_count += 1
                    
            except Exception as e:
                failed_tests.append({
                    'test_id': test_id,
                    'column': col_key,
                    'error': str(e)
                })
        
        # Step 5: Commit changes
        abrs_conn.commit()
        abrs_cursor.close()
        abrs_conn.close()
        
        # Step 6: Return result
        if failed_tests:
            return {
                'success': False,
                'message': f'Pushed {success_count} test(s), but {len(failed_tests)} failed',
                'success_count': success_count,
                'failed_tests': failed_tests
            }
        
        if success_count == 0:
            return {
                'success': False,
                'message': 'No data to push. All values are empty or rows do not exist.',
                'success_count': 0
            }
        
        return {
            'success': True,
            'message': f'Successfully pushed {success_count} test values to ABRS database',
            'success_count': success_count
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error pushing data: {str(e)}'
        }
```

## API Layer (abrs_api_views.py)

### API Endpoint
```python
@csrf_exempt
@require_http_methods(["POST"])
def api_push_data(request):
    """
    API endpoint to push test data from local database to ABRS database
    POST /api/abrs/push-data/
    
    Request Body:
    {
        "serial_no": "ABC123",
        "assembly_no": "12345"
    }
    
    Response:
    {
        "status": "success",
        "message": "Successfully pushed X test values",
        "success_count": X,
        "serial_no": "ABC123",
        "assembly_no": "12345"
    }
    """
    try:
        # Step 1: Parse request data
        data = _get_json_data(request)
        serial_no = data.get('serial_no')
        assembly_no = data.get('assembly_no')
        
        # Step 2: Validate parameters
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
        
        # Step 3: Call service layer
        result = ABRSService.push_data_to_abrs(serial_no, assembly_no)
        
        print(f"Push result: {result}")
        
        # Step 4: Handle success
        if result['success']:
            # Update status to 3 (Test Performed & Pushed)
            status_result = ABRSService.update_status(serial_no, 3)
            
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'success_count': result.get('success_count', 0),
                'serial_no': serial_no,
                'assembly_no': assembly_no
            })
        else:
            # Step 5: Handle error
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
```

### Helper Function
```python
def _get_json_data(request):
    """Helper to parse JSON from request body"""
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}
```

## URL Configuration (abrs_api_urls.py)

```python
from django.urls import path
from bray_app.views.api.abrs_api_views import (
    api_push_data,
    # ... other imports
)

urlpatterns = [
    path('push-data/', api_push_data, name='api_abrs_push_data'),
    # ... other routes
]
```

## Test Parameter Mapping

| Column | Test Detail ID | Parameter Name |
|--------|----------------|----------------|
| COL1_VALUE | 9 | Open Torque |
| COL2_VALUE | 7 | Close Torque |
| COL3_VALUE | 2 | Valve Cycle Test |
| COL4_VALUE | 11 | Hydro Shell Test Result |
| COL5_VALUE | 12 | Hydro Shell Test Duration |
| COL6_VALUE | 35 | Hydro Seat P Test Result |
| COL7_VALUE | 36 | Hydro Seat P Test Duration |
| COL8_VALUE | 31 | Hydro Seat N Test Result |
| COL9_VALUE | 32 | Hydro Seat N Test Duration |
| COL10_VALUE | 19 | Air Seat P Test Result |
| COL11_VALUE | 20 | Air Seat P Test Duration |
| COL12_VALUE | 15 | Air Seat N Test Result |
| COL13_VALUE | 16 | Air Seat N Test Duration |

## Database Queries

### Read from Local Database
```sql
SELECT SERIAL_NO, ASSEMBLY_NO, STATUS,
       COL1_VALUE, COL2_VALUE, COL3_VALUE, COL4_VALUE, COL5_VALUE,
       COL6_VALUE, COL7_VALUE, COL8_VALUE, COL9_VALUE, COL10_VALUE,
       COL11_VALUE, COL12_VALUE, COL13_VALUE
FROM abrs_result_status
WHERE SERIAL_NO = ? AND ASSEMBLY_NO = ?
```

### Check if Row Exists in ABRS
```sql
SELECT COUNT(*) FROM abrsAssemblyTest 
WHERE assemblyId = ? AND testDetailId = ?
```

### Update ABRS Database
```sql
UPDATE abrsAssemblyTest 
SET testValue = ?, 
    updatedBy = 'Teslead-100MT', 
    updatedDate = GETDATE()
WHERE assemblyId = ? AND testDetailId = ?
```

### Update Status in Local Database
```sql
UPDATE abrs_result_status 
SET STATUS = 3
WHERE SERIAL_NO = ?
```

## Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 0 | Not Performed | Test not started |
| 1 | Running | Test in progress |
| 2 | Test Performed | Ready to push |
| 3 | Test Performed & Pushed | Already pushed |

## Button States

| Status | Assembly | Button Text | Color | Enabled |
|--------|----------|-------------|-------|---------|
| 0 | Yes | Push | Gray | No |
| 1 | Yes | Push | Gray | No |
| 2 | Yes | Push | Green | Yes |
| 3 | Yes | Re-Pushed | Orange | Yes |
| Any | No | Get Assembly | Orange | Yes |

## Complete Flow Example

### User Action
1. User views ABRS table
2. Sees serial "ABC123" with Assembly "16618957" and Status = 2 (Test Performed)
3. Clicks green "Push" button

### Frontend Processing
```javascript
// 1. Confirmation dialog appears
pushToAbrs('ABC123', '16618957')

// 2. User clicks "Yes, Push"

// 3. Loading spinner shows:
// "Pushing Data..."
// "Serial: ABC123"
// "Assembly: 16618957"

// 4. AJAX POST request
fetch('/api/abrs/push-data/', {
  method: 'POST',
  body: JSON.stringify({
    serial_no: 'ABC123',
    assembly_no: '16618957'
  })
})
```

### Backend Processing
```python
# 1. API receives request
api_push_data(request)

# 2. Validates parameters
serial_no = 'ABC123'
assembly_no = '16618957'

# 3. Calls service
ABRSService.push_data_to_abrs('ABC123', '16618957')

# 4. Reads local database
SELECT COL1_VALUE, COL2_VALUE, ... FROM abrs_result_status
WHERE SERIAL_NO = 'ABC123'

# Result:
# COL1_VALUE = '10.5'
# COL2_VALUE = '8.3'
# COL3_VALUE = 'Pass'
# ... etc

# 5. Connects to ABRS
abrs_conn = get_abrs_connection()

# 6. For each column (13 times):
for col in ['col1', 'col2', ... 'col13']:
    # Check if row exists
    SELECT COUNT(*) FROM abrsAssemblyTest 
    WHERE assemblyId = '16618957' AND testDetailId = 9
    
    # If exists, update
    UPDATE abrsAssemblyTest 
    SET testValue = '10.5', 
        updatedBy = 'Teslead-100MT', 
        updatedDate = GETDATE()
    WHERE assemblyId = '16618957' AND testDetailId = 9

# 7. Commit changes
abrs_conn.commit()

# 8. Update status
UPDATE abrs_result_status 
SET STATUS = 3 
WHERE SERIAL_NO = 'ABC123'

# 9. Return success
return {
    'success': True,
    'message': 'Successfully pushed 13 test values',
    'success_count': 13
}
```

### Frontend Response
```javascript
// 1. Success message appears
Swal.fire({
  icon: 'success',
  title: 'Data Pushed Successfully!',
  html: 'Serial: ABC123, Assembly: 16618957, Test values pushed to ABRS'
})

// 2. Table refreshes
loadTableData()

// 3. Button changes:
// - Text: "Push" → "Re-Pushed"
// - Color: Green → Orange
// - Status: 2 → 3
```

## Error Handling

### Empty Values
```
If all COL1-COL13 are empty:
- Message: "No data to push. All values are empty or rows do not exist."
- Action: Complete tests first
```

### Row Doesn't Exist
```
If testDetailId row doesn't exist in ABRS:
- Skips that test parameter
- Continues with other tests
- Example: If testDetailId=31 doesn't exist, skips COL8
```

### Connection Error
```
If ABRS database connection fails:
- Message: "ABRS database error: [error details]"
- Action: Check ABRS connection
```

### Partial Failure
```
If some tests succeed, some fail:
- Message: "Pushed 10 test(s), but 3 failed"
- Shows first 3 error details
- Action: Review failed_tests array
```

## Testing

### Test Push Function
```javascript
// In browser console
pushToAbrs('TEST123', '16618957')
```

### Test API Directly
```bash
curl -X POST http://localhost:8000/api/abrs/push-data/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your_token" \
  -d '{"serial_no": "TEST123", "assembly_no": "16618957"}'
```

### Verify in Database
```sql
-- Check local database
SELECT SERIAL_NO, ASSEMBLY_NO, STATUS 
FROM abrs_result_status 
WHERE SERIAL_NO = 'TEST123';

-- Check ABRS database
SELECT assemblyId, testDetailId, testValue, updatedBy, updatedDate
FROM abrsAssemblyTest 
WHERE assemblyId = '16618957'
ORDER BY testDetailId;
```

## Summary

✅ **Frontend:** User clicks Push → Confirmation → Loading → Success/Error
✅ **API:** Validates → Calls Service → Returns JSON
✅ **Service:** Reads Local DB → Updates ABRS DB → Updates Status
✅ **Database:** UPDATE only (no INSERT) → Skips if row doesn't exist
✅ **Response:** Shows Serial + Assembly in all messages
✅ **Status:** Auto-updates from 2 → 3 after successful push

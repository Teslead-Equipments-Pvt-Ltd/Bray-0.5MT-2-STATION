# ABRS Integration Summary

## Overview
Successfully converted jQuery to vanilla JavaScript with JSON API calls and integrated ABRS database synchronization functionality. The system syncs serial numbers from the Bray ABRS SQL Server database to the local Teslead MySQL database.

## Database Connections

### Bray ABRS Database (SQL Server)
- **Server:** AZWSQL01
- **Database:** bray_AppInit
- **Driver:** ODBC Driver 18 for SQL Server
- **Table:** abrsAssembly

### Teslead Local Database (MySQL)
- **Server:** localhost:3306
- **Database:** qnq
- **Driver:** MySQL ODBC 9.0 ANSI Driver
- **Table:** abrs_serial_number

## Files Created

### 1. Service Layer
**File:** `standard_app/services/abrs_service.py`

**Methods:**
- `get_bray_connection()` - Connect to Bray ABRS SQL Server
- `get_teslead_connection()` - Connect to local MySQL database
- `sync_serials_by_date(date)` - Sync serials from a specific date
- `sync_serials_by_date_range(from_date, to_date)` - Sync serials by date range
- `search_serials(query)` - Search local serials (autocomplete)
- `get_serial_details(serial_number)` - Get serial details from local DB

**Key Features:**
- Connects to both Bray ABRS and local Teslead databases
- Fetches serial numbers from ABRS based on date/date range
- Checks for duplicates before inserting
- Only inserts new serial numbers (avoids duplicates)
- Returns detailed sync results with counts

### 2. API Views
**File:** `standard_app/views/api/abrs_api_views.py`

**Endpoints:**
- `api_import_by_date()` - POST: Sync by date range
- `api_import_by_serial()` - POST: Get serial details
- `api_search_serials()` - GET: Autocomplete search
- `api_serial_details()` - GET: Get specific serial details
- `api_sync_by_single_date()` - POST: Sync by single date

### 3. API URLs
**File:** `standard_app/urls/api/abrs_api_urls.py`

**Routes:**
- `/api/abrs/import-by-date/` - Sync by date range
- `/api/abrs/import-by-serial/` - Get serial info
- `/api/abrs/search-serials/` - Search autocomplete
- `/api/abrs/serial-details/<serial>/` - Get details
- `/api/abrs/sync-by-date/` - Sync by single date

### 4. Page Views
**File:** `standard_app/views/pages/abrs_page_views.py`
- `abrs_page()` - Renders the ABRS template with login required

### 5. Page URLs
**File:** `standard_app/urls/pages/abrs_page_urls.py`
- `/abrs/` - ABRS page route

### 6. Template
**File:** `standard_app/templates/abrs.html`
- Converted jQuery to vanilla JavaScript
- Uses Fetch API with JSON payloads
- CSRF token handling
- Async/await error handling
- SweetAlert2 for notifications

### 7. Main URLs
**File:** `standard_soft/urls.py`
- Added ABRS page routes
- Added ABRS API routes

## API Endpoints

### 1. Sync by Date Range
```http
POST /api/abrs/import-by-date/
Content-Type: application/json

{
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully synced 15 serial numbers",
  "updated_count": 15,
  "total_scanned": 20,
  "serials": [
    {
      "serial": "032401234",
      "assembly_id": "ASM123"
    }
  ]
}
```

### 2. Sync by Single Date
```http
POST /api/abrs/sync-by-date/
Content-Type: application/json

{
  "date": "2024-01-15"
}
```

### 3. Get Serial Details
```http
POST /api/abrs/import-by-serial/
Content-Type: application/json

{
  "serial_number": "032401234"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Serial number found",
  "data": {
    "serial": "032401234",
    "assembly_id": "ASM123",
    "status": "Active",
    "type": "Valve"
  }
}
```

### 4. Search Serials (Autocomplete)
```http
GET /api/abrs/search-serials/?q=0324
```

**Response:**
```json
{
  "status": "success",
  "serials": [
    {
      "number": "032401234",
      "type": "valve",
      "displayType": "Valve",
      "assembly_id": "ASM123"
    }
  ]
}
```

## How It Works

### Sync Process
1. User selects date or date range in the UI
2. Frontend sends JSON request to API endpoint
3. API calls `ABRSService` method
4. Service connects to Bray ABRS SQL Server
5. Fetches serial numbers matching criteria
6. For each serial:
   - Checks if it exists in local database
   - If not exists, inserts into `abrs_serial_number` table
   - Tracks updated count
7. Returns results to frontend
8. Frontend displays success message with count

### Serial Number Format
- Format: `03{YY}{XXXXX}` (e.g., `032401234`)
- First 2 digits: `03` (prefix)
- Next 2 digits: Year (e.g., `24` for 2024)
- Remaining: Sequential number

## Database Schema

### Local Table: `abrs_serial_number`
```sql
CREATE TABLE abrs_serial_number (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serialNumber VARCHAR(50) UNIQUE,
    assemblyId VARCHAR(50),
    serial_status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Access the Page

Navigate to: `http://localhost:8000/abrs/`

## Requirements

### Python Packages
```bash
pip install pyodbc
```

### ODBC Drivers
- **SQL Server:** ODBC Driver 18 for SQL Server
- **MySQL:** MySQL ODBC 9.0 ANSI Driver

## Security Notes

⚠️ **Important:** The database credentials are currently hardcoded in the service file. For production:
1. Move credentials to environment variables
2. Use Django settings for database configuration
3. Implement connection pooling
4. Add proper error logging
5. Use parameterized queries to prevent SQL injection

## Testing

1. **Test Date Sync:**
   - Go to `/abrs/`
   - Select "Search by Date"
   - Enter date range
   - Click "Import by Date"

2. **Test Serial Search:**
   - Select "Search by Serial Number"
   - Type serial number
   - See autocomplete suggestions
   - Click "Import Serial"

## Troubleshooting

### Connection Issues
- Verify ODBC drivers are installed
- Check database credentials
- Ensure network access to SQL Server
- Test MySQL connection locally

### No Results
- Check date format (YYYY-MM-DD)
- Verify data exists in ABRS database
- Check serial number format

### Duplicate Errors
- System automatically prevents duplicates
- Check `abrs_serial_number` table for existing records

## Next Steps

1. ✅ Convert jQuery to vanilla JavaScript
2. ✅ Create service layer with database connections
3. ✅ Implement sync functionality
4. ✅ Create API endpoints
5. ✅ Connect URLs and views
6. 🔲 Move credentials to environment variables
7. 🔲 Add comprehensive error logging
8. 🔲 Implement connection pooling
9. 🔲 Add unit tests
10. 🔲 Add permission decorators if needed

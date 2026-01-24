# ABRS Setup Guide

## Quick Start

### 1. Install Required Package
```bash
pip install pyodbc
```

### 2. Verify ODBC Drivers

**Windows:**
- SQL Server: ODBC Driver 18 for SQL Server
- MySQL: MySQL ODBC 9.0 ANSI Driver

Check installed drivers:
```bash
# PowerShell
Get-OdbcDriver
```

### 3. Database Setup

Create the local table if it doesn't exist:

```sql
CREATE TABLE IF NOT EXISTS abrs_serial_number (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serialNumber VARCHAR(50) UNIQUE NOT NULL,
    assemblyId VARCHAR(50),
    serial_status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_serial (serialNumber),
    INDEX idx_status (serial_status)
);
```

### 4. Test the Integration

#### Option A: Using the Web Interface
1. Start Django server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to: `http://localhost:8000/abrs/`

3. Test Date Range Import:
   - Select "Search by Date"
   - Enter From Date: `2024-01-01`
   - Enter To Date: `2024-12-31`
   - Click "Import by Date"

4. Test Serial Search:
   - Select "Search by Serial Number"
   - Type a serial number (e.g., `0324`)
   - Select from autocomplete
   - Click "Import Serial"

#### Option B: Using API Directly

**Test Date Range Sync:**
```bash
curl -X POST http://localhost:8000/api/abrs/import-by-date/ \
  -H "Content-Type: application/json" \
  -d '{"from_date": "2024-01-01", "to_date": "2024-12-31"}'
```

**Test Serial Search:**
```bash
curl http://localhost:8000/api/abrs/search-serials/?q=0324
```

**Test Serial Details:**
```bash
curl -X POST http://localhost:8000/api/abrs/import-by-serial/ \
  -H "Content-Type: application/json" \
  -d '{"serial_number": "032401234"}'
```

### 5. Verify Data

Check if serials were imported:
```sql
SELECT * FROM abrs_serial_number ORDER BY created_at DESC LIMIT 10;
```

## File Structure

```
standard_app/
├── services/
│   └── abrs_service.py          # Database sync logic
├── views/
│   ├── api/
│   │   └── abrs_api_views.py    # API endpoints
│   └── pages/
│       └── abrs_page_views.py   # Page rendering
├── urls/
│   ├── api/
│   │   └── abrs_api_urls.py     # API routes
│   └── pages/
│       └── abrs_page_urls.py    # Page routes
└── templates/
    └── abrs.html                # Frontend UI

standard_soft/
└── urls.py                      # Main URL config
```

## Configuration

### Environment Variables (Recommended)

Create a `.env` file:
```env
# Bray ABRS Database
BRAY_DB_SERVER=AZWSQL01
BRAY_DB_NAME=bray_AppInit
BRAY_DB_USER=Teslead
BRAY_DB_PASSWORD=W0gK!Lv$kTk%91

# Teslead Local Database
TESLEAD_DB_HOST=localhost
TESLEAD_DB_PORT=3306
TESLEAD_DB_NAME=qnq
TESLEAD_DB_USER=root
TESLEAD_DB_PASSWORD=477f9aeeb4c9f39a11b2a1d8382e2b58
```

Update `abrs_service.py` to use environment variables:
```python
import os
from dotenv import load_dotenv

load_dotenv()

@staticmethod
def get_bray_connection():
    bray_driver_bridge = pyodbc.connect(
        f'DRIVER={{ODBC Driver 18 for SQL Server}};'
        f'SERVER={os.getenv("BRAY_DB_SERVER")};'
        f'UID={os.getenv("BRAY_DB_USER")};'
        f'PWD={os.getenv("BRAY_DB_PASSWORD")};'
        f'DATABASE={os.getenv("BRAY_DB_NAME")};'
        f'TrustServerCertificate=yes;'
    )
    return bray_driver_bridge.cursor()
```

## Troubleshooting

### Issue: "pyodbc.Error: Data source name not found"
**Solution:** Install the required ODBC driver
- SQL Server: Download from Microsoft
- MySQL: Download from MySQL website

### Issue: "Connection timeout"
**Solution:** 
- Check network connectivity to SQL Server
- Verify firewall rules
- Test connection with SQL Server Management Studio

### Issue: "Access denied for user"
**Solution:**
- Verify database credentials
- Check user permissions
- Ensure user has INSERT privileges

### Issue: "Table doesn't exist"
**Solution:**
- Run the CREATE TABLE script
- Verify database name is correct

### Issue: "Duplicate entry"
**Solution:**
- This is expected behavior
- System prevents duplicate serials automatically
- Check existing records in database

## API Response Examples

### Success Response
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

### Error Response
```json
{
  "status": "error",
  "message": "Failed to connect to databases"
}
```

## Performance Tips

1. **Use Date Ranges Wisely:** Smaller date ranges = faster sync
2. **Index Your Tables:** Ensure indexes on `serialNumber` column
3. **Connection Pooling:** Consider implementing for production
4. **Batch Processing:** For large datasets, process in batches

## Security Checklist

- [ ] Move credentials to environment variables
- [ ] Use parameterized queries (already implemented)
- [ ] Add rate limiting to API endpoints
- [ ] Implement proper logging
- [ ] Add authentication/authorization checks
- [ ] Use HTTPS in production
- [ ] Encrypt sensitive data at rest

## Monitoring

Add logging to track sync operations:

```python
import logging

logger = logging.getLogger(__name__)

# In sync method
logger.info(f"Starting sync for date range: {from_date} to {to_date}")
logger.info(f"Synced {updated_count} new serials")
logger.error(f"Sync failed: {str(e)}")
```

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify database connections
3. Test API endpoints individually
4. Review ABRS_INTEGRATION.md for detailed documentation

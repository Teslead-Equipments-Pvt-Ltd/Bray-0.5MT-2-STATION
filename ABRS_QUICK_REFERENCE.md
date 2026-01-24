# ABRS Quick Reference

## URLs

| Type | URL | Method | Description |
|------|-----|--------|-------------|
| Page | `/abrs/` | GET | ABRS UI page |
| API | `/api/abrs/import-by-date/` | POST | Sync by date range |
| API | `/api/abrs/sync-by-date/` | POST | Sync by single date |
| API | `/api/abrs/import-by-serial/` | POST | Get serial details |
| API | `/api/abrs/search-serials/?q=` | GET | Search autocomplete |
| API | `/api/abrs/serial-details/<serial>/` | GET | Get specific serial |

## API Examples

### Sync by Date Range
```bash
curl -X POST http://localhost:8000/api/abrs/import-by-date/ \
  -H "Content-Type: application/json" \
  -d '{
    "from_date": "2024-01-01",
    "to_date": "2024-12-31"
  }'
```

### Sync by Single Date
```bash
curl -X POST http://localhost:8000/api/abrs/sync-by-date/ \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-01-15"
  }'
```

### Search Serials
```bash
curl http://localhost:8000/api/abrs/search-serials/?q=0324
```

### Get Serial Details
```bash
curl -X POST http://localhost:8000/api/abrs/import-by-serial/ \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "032401234"
  }'
```

## JavaScript Fetch Examples

### Import by Date Range
```javascript
const response = await fetch('/api/abrs/import-by-date/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken()
  },
  body: JSON.stringify({
    from_date: '2024-01-01',
    to_date: '2024-12-31'
  })
});

const data = await response.json();
console.log(data.updated_count); // Number of new serials
```

### Search Serials (Autocomplete)
```javascript
const response = await fetch(`/api/abrs/search-serials/?q=${query}`);
const data = await response.json();
console.log(data.serials); // Array of matching serials
```

## Database Queries

### Check Recent Imports
```sql
SELECT * FROM abrs_serial_number 
ORDER BY created_at DESC 
LIMIT 10;
```

### Count Total Serials
```sql
SELECT COUNT(*) as total FROM abrs_serial_number;
```

### Find Specific Serial
```sql
SELECT * FROM abrs_serial_number 
WHERE serialNumber = '032401234';
```

### Get Serials by Date
```sql
SELECT * FROM abrs_serial_number 
WHERE DATE(created_at) = '2024-01-15';
```

### Active Serials Only
```sql
SELECT * FROM abrs_serial_number 
WHERE serial_status = 1;
```

## Service Methods

```python
from standard_app.services.abrs_service import ABRSService

# Sync by date range
result = ABRSService.sync_serials_by_date_range('2024-01-01', '2024-12-31')

# Sync by single date
result = ABRSService.sync_serials_by_date('2024-01-15')

# Search serials
serials = ABRSService.search_serials('0324')

# Get serial details
details = ABRSService.get_serial_details('032401234')
```

## Response Structures

### Sync Response
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

### Search Response
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

### Details Response
```json
{
  "status": "success",
  "data": {
    "serial": "032401234",
    "assembly_id": "ASM123",
    "status": "Active",
    "type": "Valve"
  }
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description here"
}
```

## Common Tasks

### Add to Navigation Menu
```html
<!-- In base_new.html or navigation template -->
<li class="nav-item">
  <a class="nav-link" href="{% url 'abrs' %}">
    <i class="fas fa-sync"></i> ABRS Sync
  </a>
</li>
```

### Add Permission Check
```python
# In abrs_page_views.py
from standard_app.decorators import permission_required

@login_required
@permission_required("ABRS")
def abrs_page(request):
    # ...
```

### Custom Date Format
```javascript
// Format date for display
const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};
```

## Testing Checklist

- [ ] Test date range sync with valid dates
- [ ] Test date range sync with invalid dates
- [ ] Test single date sync
- [ ] Test serial search autocomplete
- [ ] Test serial details lookup
- [ ] Test duplicate prevention
- [ ] Test error handling
- [ ] Test UI responsiveness
- [ ] Test CSRF token handling
- [ ] Verify database connections

## File Locations

```
Services:     standard_app/services/abrs_service.py
API Views:    standard_app/views/api/abrs_api_views.py
Page Views:   standard_app/views/pages/abrs_page_views.py
API URLs:     standard_app/urls/api/abrs_api_urls.py
Page URLs:    standard_app/urls/pages/abrs_page_urls.py
Template:     standard_app/templates/abrs.html
Main URLs:    standard_soft/urls.py
```

## Dependencies

```txt
pyodbc>=4.0.0
Django>=4.0.0
python-dotenv>=0.19.0  # Optional, for env vars
```

## Environment Setup

```bash
# Install dependencies
pip install pyodbc python-dotenv

# Verify ODBC drivers
# Windows PowerShell:
Get-OdbcDriver

# Test database connections
python manage.py shell
>>> from standard_app.services.abrs_service import ABRSService
>>> bray_db = ABRSService.get_bray_connection()
>>> teslead_db = ABRSService.get_teslead_connection()
```

## Logs Location

Check Django logs for sync operations:
```bash
# Development
python manage.py runserver --verbosity 2

# Production
tail -f /var/log/django/abrs.log
```

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check ODBC drivers installed |
| Access denied | Verify database credentials |
| No results | Check date format and data exists |
| Duplicate error | Normal - system prevents duplicates |
| Timeout | Check network/firewall settings |

## Performance Metrics

- Average sync time: ~2-5 seconds per 100 serials
- Recommended batch size: 1000 serials per request
- Database query optimization: Indexed on serialNumber
- Connection timeout: 30 seconds default

## Next Steps

1. Test the integration with real data
2. Add logging for production monitoring
3. Implement connection pooling
4. Add rate limiting
5. Create backup/restore procedures
6. Document business processes
7. Train users on the interface

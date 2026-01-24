# Alarm System - Debugging Guide

## Issue: Alarms Not Showing in Frontend

### ✅ Fixes Applied

1. **Added `id="alarmsList"` to HTML**
   - The JavaScript was looking for `getElementById('alarmsList')` but the HTML didn't have this ID
   - Fixed in `dashboard_new.html`

2. **Corrected Table Name**
   - Using `alarm_status` table (not `alarm_history`)
   - Column name: `created_time` (not `ALARM_TIME`)

3. **Added Debug Logging**
   - Backend logs in Django console
   - Frontend logs in browser console

## 🔍 How to Debug

### Step 1: Check Django Console Logs

When you refresh the dashboard, you should see these logs in your Django console:

```
DEBUG: Found X alarms in alarm_status table
DEBUG: Processing alarm - Name: Emergency Stop, Time: 2024-12-12 10:30:00
DEBUG: Returning X alarms to frontend
DEBUG: recent_alarms = [{'alarm_name': 'Emergency Stop', 'time_ago': '2 hrs ago'}]
```

**If you see 0 alarms:**
- The `alarm_status` table is empty
- Check if alarms are being inserted when HMI sends alarm signals

### Step 2: Check Browser Console Logs

Open browser console (F12) and look for:

```javascript
API Response: {hmi_connection: 1, abrs_connection: 0, alarm_s1: 1, ...}
Recent alarms: [{alarm_name: "Emergency Stop", time_ago: "2 hrs ago"}]
Updating alarms display with 4 alarms
```

**If you see "No alarms to display":**
- The API is not returning `recent_alarms` array
- Check Django console logs

### Step 3: Check Database

Verify data exists in the table:

```sql
-- Check if table exists
SHOW TABLES LIKE 'alarm_status';

-- Check table structure
DESCRIBE alarm_status;

-- Check data
SELECT * FROM alarm_status ORDER BY created_time DESC LIMIT 10;

-- Count records
SELECT COUNT(*) FROM alarm_status;
```

**Expected columns:**
- `ALARM_CODE` (or `id`)
- `ALARM_NAME`
- `created_time`

### Step 4: Test API Directly

Test the API endpoint directly:

```bash
curl http://localhost:8000/api/user_config/get_hmi_abrs/
```

**Expected Response:**
```json
{
  "hmi_connection": 1,
  "abrs_connection": 0,
  "alarm_s1": 1,
  "alarm_s1_name": "Emergency Stop",
  "alarm_s2": 0,
  "alarm_s2_name": null,
  "recent_alarms": [
    {
      "alarm_name": "Emergency Stop",
      "time_ago": "2 hrs ago"
    }
  ]
}
```

## 🐛 Common Issues

### Issue 1: Empty `recent_alarms` Array

**Cause:** No data in `alarm_status` table

**Solution:**
```sql
-- Insert test data
INSERT INTO alarm_status (ALARM_CODE, ALARM_NAME, created_time) 
VALUES 
(1, 'Emergency Stop', NOW()),
(2, 'Water Level Low', DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(3, 'Maximum Tonnage', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(4, 'Select Test Type', DATE_SUB(NOW(), INTERVAL 1 DAY));
```

### Issue 2: "Loading alarms..." Never Changes

**Cause:** JavaScript not finding the `alarmsList` element

**Solution:** Verify HTML has:
```html
<div class="alerts-list" id="alarmsList">
```

### Issue 3: Alarms Not Updating

**Cause:** HMI not sending alarm signals or alarm value is 0

**Solution:**
- Check HMI connection status (should show "HMI Connected")
- Verify HMI addresses 2035 and 2133 are sending values > 0
- Check Django logs for "Processing alarm" messages

### Issue 4: Wrong Table/Column Names

**Cause:** Database schema doesn't match code

**Solution:** Verify your actual table structure:
```sql
DESCRIBE alarm_status;
```

If columns are different, update the query in `configuration_api_views.py`:
```python
cursor.execute("""
    SELECT ALARM_NAME, created_time 
    FROM alarm_status 
    ORDER BY created_time DESC 
    LIMIT 4
""")
```

## 📋 Checklist

Before reporting an issue, verify:

- [ ] `alarm_status` table exists
- [ ] Table has data (run `SELECT * FROM alarm_status`)
- [ ] HMI is connected (dashboard shows "HMI Connected")
- [ ] Django console shows debug logs
- [ ] Browser console shows API response
- [ ] HTML has `id="alarmsList"`
- [ ] No JavaScript errors in browser console
- [ ] API endpoint returns `recent_alarms` array

## 🔧 Quick Fixes

### Fix 1: Force Display Test Alarms

Add this to browser console to test frontend display:

```javascript
updateAlarmsDisplay([
  {alarm_name: "Test Alarm 1", time_ago: "2 hrs ago"},
  {alarm_name: "Test Alarm 2", time_ago: "1 day ago"}
]);
```

If this works, the issue is with the API/backend.

### Fix 2: Check API Response

Add this to browser console:

```javascript
fetch('/api/user_config/get_hmi_abrs/')
  .then(r => r.json())
  .then(d => console.log('API Response:', d));
```

Check if `recent_alarms` is in the response.

### Fix 3: Verify Table Name

If your table has a different name, update both files:

**In `user_config_service.py`:**
```python
cursor.execute("""
    SELECT ALARM_NAME, created_time 
    FROM your_table_name 
    ORDER BY created_time DESC 
    LIMIT 4
""")
```

**In `configuration_api_views.py`:**
```python
cursor.execute("""
    SELECT ALARM_NAME, created_time 
    FROM your_table_name 
    ORDER BY created_time DESC 
    LIMIT 4
""")
```

## 📊 Expected Behavior

When everything works correctly:

1. **Every 5 seconds:**
   - Dashboard calls `/api/user_config/get_hmi_abrs/`
   - API reads HMI addresses 2035 and 2133
   - If alarm value > 0, inserts into `alarm_status`
   - Returns recent 4 alarms

2. **Frontend:**
   - Receives `recent_alarms` array
   - Calls `updateAlarmsDisplay()`
   - Renders alarms with alternating red/yellow styling

3. **Display:**
   - Shows alarm name and time ago
   - Updates every 5 seconds
   - No page reload needed

## 🎯 Next Steps

1. **Check Django Console** - Look for debug logs
2. **Check Browser Console** - Look for API response
3. **Check Database** - Verify data exists
4. **Test API** - Use curl or browser
5. **Insert Test Data** - If table is empty

If alarms still don't show after these steps, share:
- Django console logs
- Browser console logs
- Database query results
- API response

This will help identify the exact issue!

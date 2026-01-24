# Alarm Query Fixes - Summary

## ✅ Issues Found and Fixed

### 1. SQL Syntax Errors in `user_config_service.py`

#### ❌ Original Code (INCORRECT)
```python
def get_alarmname_s1(alarm_s1):
    with connection.cursor() as cursor:
        cursor.execute("select ALARM_NAME from alarm where ALARM_ID=%s",[alarm_s1])
        alarm_name = cursor.fetchone()
        
        # WRONG: Mixing SET and VALUES syntax
        cursor.execute("insert into alarm_status set (ALARM_CODE,ALARM_NAME) values(%s,%s)",[alarm_s1,alarm_name])
        
        # WRONG: Ordering by name instead of time
        cursor.execute("select ALARM_NAME from alarm_status order by ALARM_NAME desc limit 4")
        return cursor.fetchall()
```

**Problems:**
1. ❌ `INSERT INTO ... SET ... VALUES` - Invalid syntax (mixing SET and VALUES)
2. ❌ `ORDER BY ALARM_NAME DESC` - Should order by timestamp, not name
3. ❌ Table name `alarm` should be `alarm_table`
4. ❌ Table name `alarm_status` should be `alarm_history`
5. ❌ Missing `get_alarmname_s2()` function

#### ✅ Fixed Code (CORRECT)
```python
def get_alarmname_s1(alarm_s1):
    """Get alarm name for station 1 and log it"""
    try:
        with connection.cursor() as cursor:
            # Get alarm name from alarm_table
            cursor.execute("SELECT ALARM_NAME FROM alarm_table WHERE ALARM_ID=%s", [alarm_s1])
            result = cursor.fetchone()
            alarm_name = result[0] if result else f"Unknown Alarm {alarm_s1}"
            
            # Correct INSERT syntax
            cursor.execute("""
                INSERT INTO alarm_history (ALARM_ID, ALARM_CODE, ALARM_NAME, ALARM_TIME) 
                VALUES (%s, %s, %s, NOW())
            """, [alarm_s1, f"ALM{alarm_s1:03d}", alarm_name])
            
            # Order by time, not name
            cursor.execute("""
                SELECT ALARM_NAME, ALARM_TIME 
                FROM alarm_history 
                ORDER BY ALARM_TIME DESC 
                LIMIT 4
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error in get_alarmname_s1: {e}")
        return []

def get_alarmname_s2(alarm_s2):
    """Get alarm name for station 2 and log it"""
    try:
        with connection.cursor() as cursor:
            # Get alarm name from alarm_table
            cursor.execute("SELECT ALARM_NAME FROM alarm_table WHERE ALARM_ID=%s", [alarm_s2])
            result = cursor.fetchone()
            alarm_name = result[0] if result else f"Unknown Alarm {alarm_s2}"
            
            # Correct INSERT syntax
            cursor.execute("""
                INSERT INTO alarm_history (ALARM_ID, ALARM_CODE, ALARM_NAME, ALARM_TIME) 
                VALUES (%s, %s, %s, NOW())
            """, [alarm_s2, f"ALM{alarm_s2:03d}", alarm_name])
            
            # Order by time, not name
            cursor.execute("""
                SELECT ALARM_NAME, ALARM_TIME 
                FROM alarm_history 
                ORDER BY ALARM_TIME DESC 
                LIMIT 4
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error in get_alarmname_s2: {e}")
        return []
```

### 2. Missing Import in `configuration_api_views.py`

#### ❌ Original
```python
from bray_app.services.user_config_service import (
    ..., get_alarmname_s1
)
```

#### ✅ Fixed
```python
from bray_app.services.user_config_service import (
    ..., get_alarmname_s1, get_alarmname_s2
)
```

### 3. Alarm Data Not Returned to Frontend

#### ❌ Original
```python
get_alarmname_s1(alarm_s1)
get_alarmname_s2(alarm_s2)

return JsonResponse({
    "hmi_connection": hmi_status,
    "abrs_connection": abrs_connection
})
```

**Problem:** Alarm data was processed but not returned to frontend

#### ✅ Fixed
```python
# Process alarms and get recent 4
if hmi_status == 1:
    if alarm_s1_value > 0:
        alarms_s1 = get_alarmname_s1(alarm_s1_value)
        if alarms_s1 and len(alarms_s1) > 0:
            alarm_s1_name = alarms_s1[0][0]
    
    if alarm_s2_value > 0:
        alarms_s2 = get_alarmname_s2(alarm_s2_value)
        if alarms_s2 and len(alarms_s2) > 0:
            alarm_s2_name = alarms_s2[0][0]
    
    # Get recent 4 alarms with time_ago calculation
    recent_alarms = [...]

return JsonResponse({
    "hmi_connection": hmi_status,
    "abrs_connection": abrs_connection,
    "alarm_s1": alarm_s1_value,
    "alarm_s1_name": alarm_s1_name,
    "alarm_s2": alarm_s2_value,
    "alarm_s2_name": alarm_s2_name,
    "recent_alarms": recent_alarms
})
```

### 4. Frontend Display Added

#### ✅ Added to `dashboard_new.html`
```javascript
// Update alarms display if available
if (data.recent_alarms && data.recent_alarms.length > 0) {
  updateAlarmsDisplay(data.recent_alarms);
}

function updateAlarmsDisplay(alarms) {
  const alarmsList = document.getElementById('alarmsList');
  
  if (!alarmsList) return;
  
  // Build alarms HTML with alternating colors
  let alarmsHtml = '';
  alarms.forEach((alarm, index) => {
    const alertClass = index % 2 === 0 ? 'alert-red' : 'alert-yellow';
    const iconSrc = index % 2 === 0 ?
      "{% static 'images/danger.png' %}" :
      "{% static 'images/danger-yellow.png' %}";
    
    alarmsHtml += `
      <div class="alert-item ${alertClass}">
        <img src="${iconSrc}" alt="Alert" class="alert-icon">
        <span class="alert-text">${alarm.alarm_name} - ${alarm.time_ago}</span>
      </div>
    `;
  });
  
  alarmsList.innerHTML = alarmsHtml;
}
```

## 📊 How It Works Now

### Data Flow
```
1. Dashboard calls /api/user_config/get_hmi_abrs/ (every 5 seconds)
   ↓
2. API reads HMI addresses:
   - 2035 (Station 1 alarm)
   - 2133 (Station 2 alarm)
   ↓
3. If alarm value > 0:
   - Query alarm_table for alarm name
   - Insert into alarm_history
   - Get recent 4 alarms
   ↓
4. Return JSON with:
   - HMI/ABRS connection status
   - Alarm values and names
   - Recent 4 alarms with time_ago
   ↓
5. Frontend displays alarms in "Recent Alerts" section
```

### Database Tables Used

**alarm_table** (Alarm Definitions)
```sql
ALARM_ID | ALARM_CODE | ALARM_NAME
1        | ALM001     | Emergency Stop
2        | ALM002     | Water Level Low
```

**alarm_history** (Alarm Logs)
```sql
ID | ALARM_ID | ALARM_CODE | ALARM_NAME      | ALARM_TIME
1  | 1        | ALM001     | Emergency Stop  | 2024-12-12 10:30:00
```

## ✅ Correct SQL Queries

### Query 1: Get Alarm Name
```sql
SELECT ALARM_NAME 
FROM alarm_table 
WHERE ALARM_ID = %s
```

### Query 2: Log Alarm
```sql
INSERT INTO alarm_history (ALARM_ID, ALARM_CODE, ALARM_NAME, ALARM_TIME) 
VALUES (%s, %s, %s, NOW())
```

### Query 3: Get Recent Alarms
```sql
SELECT ALARM_NAME, ALARM_TIME 
FROM alarm_history 
ORDER BY ALARM_TIME DESC 
LIMIT 4
```

## 🎯 Key Improvements

✅ **Correct SQL Syntax** - Fixed INSERT statement
✅ **Proper Ordering** - Order by ALARM_TIME DESC (not ALARM_NAME)
✅ **Correct Table Names** - alarm_table and alarm_history
✅ **Error Handling** - Try-catch blocks added
✅ **Station 2 Support** - Added get_alarmname_s2() function
✅ **Frontend Display** - Alarms now shown on dashboard
✅ **Time Calculation** - Human-readable "2 hrs ago" format
✅ **Single API Call** - Alarms included in connection check

## 🧪 Testing

### Test the API
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

### Test in Browser
1. Navigate to dashboard: `http://localhost:8000/dashboard/`
2. Check "Recent Alerts" section
3. Open browser console (F12) to see logs
4. Verify alarms update every 5 seconds

## 📝 Summary

All SQL queries have been corrected and the alarm system is now fully integrated into the existing connection check API. The dashboard displays recent 4 alarms with proper formatting and automatic updates every 5 seconds.

**No separate alarm API calls needed** - everything is handled in the existing `/api/user_config/get_hmi_abrs/` endpoint!

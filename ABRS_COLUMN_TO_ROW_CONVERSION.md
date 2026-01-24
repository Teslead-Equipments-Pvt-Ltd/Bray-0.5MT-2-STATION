# ABRS Data Conversion: Columns to Rows

## Understanding the Conversion

Your local database stores test data in **COLUMNS** (horizontal), but ABRS database stores them in **ROWS** (vertical).

## Visual Example

### Local Database (abrs_result_status) - COLUMN-BASED
```
┌───────────┬─────────────┬────────┬────────────┬────────────┬────────────┬─────┬─────────────┐
│ SERIAL_NO │ ASSEMBLY_NO │ STATUS │ COL1_VALUE │ COL2_VALUE │ COL3_VALUE │ ... │ COL13_VALUE │
├───────────┼─────────────┼────────┼────────────┼────────────┼────────────┼─────┼─────────────┤
│ ABC123    │ 16618957    │ 2      │ 10.5       │ 8.3        │ Pass       │ ... │ 5.2         │
└───────────┴─────────────┴────────┴────────────┴────────────┴────────────┴─────┴─────────────┘
                                    ↓            ↓            ↓                  ↓
                                    │            │            │                  │
                    ┌───────────────┘            │            │                  │
                    │               ┌────────────┘            │                  │
                    │               │            ┌────────────┘                  │
                    │               │            │            ┌──────────────────┘
                    ↓               ↓            ↓            ↓
```

### ABRS Database (testValue) - ROW-BASED
```
┌────────────┬───────────┬───────────┬──────────────────────────────────┐
│ assemblyId │ testIndId │ testValue │ Description                      │
├────────────┼───────────┼───────────┼──────────────────────────────────┤
│ 16618957   │ 9         │ 10.5      │ Open Torque (from COL1)          │
│ 16618957   │ 7         │ 8.3       │ Close Torque (from COL2)         │
│ 16618957   │ 2         │ Pass      │ Valve Cycle Test (from COL3)     │
│ 16618957   │ 11        │ OK        │ Hydro Shell Result (from COL4)   │
│ 16618957   │ 12        │ 120       │ Hydro Shell Duration (from COL5) │
│ 16618957   │ 35        │ OK        │ Hydro Seat P Result (from COL6)  │
│ 16618957   │ 36        │ 90        │ Hydro Seat P Duration (from COL7)│
│ 16618957   │ 31        │ OK        │ Hydro Seat N Result (from COL8)  │
│ 16618957   │ 32        │ 85        │ Hydro Seat N Duration (from COL9)│
│ 16618957   │ 19        │ OK        │ Air Seat P Result (from COL10)   │
│ 16618957   │ 20        │ 60        │ Air Seat P Duration (from COL11) │
│ 16618957   │ 15        │ OK        │ Air Seat N Result (from COL12)   │
│ 16618957   │ 16        │ 5.2       │ Air Seat N Duration (from COL13) │
└────────────┴───────────┴───────────┴──────────────────────────────────┘
```

## The Conversion Process

### Step 1: Read from Local Database (1 row with 13 columns)
```sql
SELECT COL1_VALUE, COL2_VALUE, COL3_VALUE, ..., COL13_VALUE
FROM abrs_result_status
WHERE SERIAL_NO = 'ABC123' AND ASSEMBLY_NO = '16618957'

Result:
COL1_VALUE = 10.5
COL2_VALUE = 8.3
COL3_VALUE = Pass
...
COL13_VALUE = 5.2
```

### Step 2: Convert Each Column to a Row in ABRS (13 rows)
```python
# For COL1_VALUE (10.5)
INSERT INTO testValue (assemblyId, testIndId, testValue)
VALUES ('16618957', 9, '10.5')

# For COL2_VALUE (8.3)
INSERT INTO testValue (assemblyId, testIndId, testValue)
VALUES ('16618957', 7, '8.3')

# For COL3_VALUE (Pass)
INSERT INTO testValue (assemblyId, testIndId, testValue)
VALUES ('16618957', 2, 'Pass')

# ... and so on for all 13 columns
```

## Complete Mapping Table

| # | Local Column | → | ABRS Row (testIndId) | Test Parameter Name |
|---|--------------|---|----------------------|---------------------|
| 1 | COL1_VALUE | → | testIndId = 9 | Open Torque |
| 2 | COL2_VALUE | → | testIndId = 7 | Close Torque |
| 3 | COL3_VALUE | → | testIndId = 2 | Valve Cycle Test |
| 4 | COL4_VALUE | → | testIndId = 11 | Hydro Shell Test Result |
| 5 | COL5_VALUE | → | testIndId = 12 | Hydro Shell Test Duration |
| 6 | COL6_VALUE | → | testIndId = 35 | Hydro Seat P Test Result |
| 7 | COL7_VALUE | → | testIndId = 36 | Hydro Seat P Test Duration |
| 8 | COL8_VALUE | → | testIndId = 31 | Hydro Seat N Test Result |
| 9 | COL9_VALUE | → | testIndId = 32 | Hydro Seat N Test Duration |
| 10 | COL10_VALUE | → | testIndId = 19 | Air Seat P Test Result |
| 11 | COL11_VALUE | → | testIndId = 20 | Air Seat P Test Duration |
| 12 | COL12_VALUE | → | testIndId = 15 | Air Seat N Test Result |
| 13 | COL13_VALUE | → | testIndId = 16 | Air Seat N Test Duration |

## Code Logic

```python
# Read 1 row with 13 columns from local DB
local_data = {
    'col1': '10.5',
    'col2': '8.3',
    'col3': 'Pass',
    # ... 13 columns total
}

# Convert to 13 rows in ABRS DB
for col_key, test_ind_id in mapping.items():
    value = local_data[col_key]
    
    # Each column becomes a separate row
    INSERT INTO testValue (assemblyId, testIndId, testValue)
    VALUES ('16618957', test_ind_id, value)
```

## Why This Design?

### Local Database (Columns):
- ✅ Easy to view all tests for one serial in one row
- ✅ Fast to query all test results at once
- ✅ Simple table structure

### ABRS Database (Rows):
- ✅ Flexible - can add new test types without changing table structure
- ✅ Easy to query specific test types across all assemblies
- ✅ Normalized database design
- ✅ Can store additional metadata per test (testResultId, testDetailsName, etc.)

## Verification Query

After pushing, verify the conversion worked:

```sql
-- Check local database (1 row, 13 columns)
SELECT SERIAL_NO, ASSEMBLY_NO, 
       COL1_VALUE, COL2_VALUE, COL3_VALUE
FROM abrs_result_status
WHERE SERIAL_NO = 'ABC123';

-- Check ABRS database (13 rows, 1 value per row)
SELECT assemblyId, testIndId, testValue
FROM testValue
WHERE assemblyId = '16618957'
ORDER BY testIndId;
```

Expected result: 13 rows in ABRS, one for each column from local database.

## Summary

✅ **1 Local Row** (13 columns) → **13 ABRS Rows** (1 value each)
✅ Each column value becomes a separate row
✅ testIndId identifies which test parameter it is
✅ assemblyId links all 13 rows together
✅ This is the correct design pattern!

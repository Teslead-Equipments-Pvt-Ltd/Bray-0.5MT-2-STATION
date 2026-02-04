from django.db import connection


def get_all_user_accounting():
    """Get all employee login/logout status records (excluding super admins) - show each login session as separate row."""
    try:
        with connection.cursor() as cursor:
            # Get all login records from employee_login_logout_status table
            # Use a more robust join to ensure we get the correct employee details
            cursor.execute("""
                SELECT 
                    COALESCE(e.code, els.employee_code) as employee_code,
                    COALESCE(e.name, els.employe_name) as employee_name,
                    COALESCE(e.employee_type, els.employee_type) as employee_type,
                    els.last_login, 
                    els.last_logout, 
                    els.id,
                    els.employee_code as original_code,
                    els.employe_name as original_name
                FROM employee_login_logout_status els
                LEFT JOIN employee e ON (
                    els.employee_code = e.code OR 
                    els.employe_name = e.name
                )
                WHERE (e.superuser = 0 OR e.superuser IS NULL)
                ORDER BY els.id DESC
            """)
            rows = cursor.fetchall()
            return [
                {
                    'code': r[0] or '',
                    'name': r[1] or '',
                    'employee_type': r[2] or '',
                    'last_login': str(r[3]) if r[3] else None,
                    'last_logout': str(r[4]) if r[4] else None,
                    'session_id': r[5],  # Add session ID for reference
                    'debug_original_code': r[6],  # For debugging
                    'debug_original_name': r[7]   # For debugging
                }
                for r in rows
            ]
    except Exception as e:
        print(f"Error in get_all_user_accounting: {e}")
        # Return empty list if there's an error
        return []


def fix_employee_login_records():
    """Fix any inconsistent employee codes in login records by matching with employee names."""
    try:
        with connection.cursor() as cursor:
            # Find records where the employee_code doesn't match the actual employee
            cursor.execute("""
                UPDATE employee_login_logout_status els
                SET employee_code = (
                    SELECT e.code 
                    FROM employee e 
                    WHERE e.name = els.employe_name 
                    LIMIT 1
                )
                WHERE EXISTS (
                    SELECT 1 
                    FROM employee e 
                    WHERE e.name = els.employe_name 
                    AND e.code != els.employee_code
                )
            """)
            
            updated_rows = cursor.rowcount
            print(f"Fixed {updated_rows} login records with incorrect employee codes")
            return updated_rows
            
    except Exception as e:
        print(f"Error fixing employee login records: {e}")
        return 0


def get_login_data_debug():
    """Debug function to see what's in the login table."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT els.id, els.employee_code, els.employe_name, els.employee_type,
                       e.code as actual_code, e.name as actual_name, e.employee_type as actual_type
                FROM employee_login_logout_status els
                LEFT JOIN employee e ON els.employe_name = e.name
                ORDER BY els.id DESC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            
            print("=== LOGIN DATA DEBUG ===")
            for r in rows:
                print(f"ID: {r[0]}, Stored Code: {r[1]}, Stored Name: {r[2]}, Stored Type: {r[3]}")
                print(f"    Actual Code: {r[4]}, Actual Name: {r[5]}, Actual Type: {r[6]}")
                print(f"    Match: {r[1] == r[4] if r[4] else 'No employee found'}")
                print("---")
            
            return rows
            
    except Exception as e:
        print(f"Error in debug function: {e}")
        return []
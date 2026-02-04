from django.db import connection
from datetime import datetime


class AuthService:

    @staticmethod
    def get_user_by_username(username):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, password, superuser, status FROM employee WHERE name = %s",
                [username]
            )
            return cursor.fetchone()  # (name, password, superuser, status)

    @staticmethod
    def get_employee_details(username):
        """Get employee code and type for login tracking."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT code, employee_type FROM employee WHERE name = %s",
                [username]
            )
            return cursor.fetchone()  # (code, employee_type)

    @staticmethod
    def verify_username(username):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, superuser FROM employee WHERE name = %s",
                [username]
            )
            return cursor.fetchone()  # (name, superuser)

    @staticmethod
    def update_password(username, hashed_password):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE employee SET password = %s WHERE name = %s",
                [hashed_password, username]
            )

    @staticmethod
    def update_logout(username, password):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE employee SET last_logout = %s WHERE name = %s AND password = %s",
                [current_time, username, password]
            )
         

    @staticmethod
    def record_login(username):
        """Record login to employee_login_logout_status table - always insert new row."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get employee details - try multiple approaches to ensure we get the right employee
        details = AuthService.get_employee_details(username)
        if not details:
            print(f"[LOGIN] No employee details found for username: {username}")
            # Try to find by code instead of name
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT code, employee_type FROM employee WHERE code = %s",
                    [username]
                )
                details = cursor.fetchone()
                if not details:
                    print(f"[LOGIN] No employee found by code either: {username}")
                    return None
        
        employee_code, employee_type = details
        print(f"[LOGIN] Found employee - Code: {employee_code}, Type: {employee_type}, Username: {username}")
        
        with connection.cursor() as cursor:
            # Always insert a new row for each login
            cursor.execute(
                """INSERT INTO employee_login_logout_status 
                   (employee_code, employe_name, employee_type, last_login) 
                   VALUES (%s, %s, %s, %s)""",
                [employee_code, username, employee_type or '', current_time]
            )
            # Get the ID of the inserted row to update logout later
            login_record_id = cursor.lastrowid
            print(f"[LOGIN] Created new login record ID: {login_record_id} for {username} with code {employee_code}")
            return login_record_id

    @staticmethod
    def record_logout(username, login_record_id=None):
        """Record logout to employee_login_logout_status table - update the login record."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get employee details - try multiple approaches
        details = AuthService.get_employee_details(username)
        if not details:
            print(f"[LOGOUT] No employee details found for username: {username}")
            # Try to find by code instead of name
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT code, employee_type FROM employee WHERE code = %s",
                    [username]
                )
                details = cursor.fetchone()
                if not details:
                    print(f"[LOGOUT] No employee found by code either: {username}")
                    return False
        
        employee_code, employee_type = details
        print(f"[LOGOUT] Recording logout for employee_code: {employee_code} (username: {username}) at {current_time}")
        
        with connection.cursor() as cursor:
            if login_record_id:
                # Update the specific login record
                cursor.execute(
                    "UPDATE employee_login_logout_status SET last_logout = %s WHERE id = %s",
                    [current_time, login_record_id]
                )
                print(f"[LOGOUT] Updated logout time for record ID: {login_record_id}")
            else:
                # Update the most recent login record for this employee (where logout is NULL)
                cursor.execute(
                    """UPDATE employee_login_logout_status 
                       SET last_logout = %s 
                       WHERE employee_code = %s AND last_logout IS NULL
                       ORDER BY id DESC LIMIT 1""",
                    [current_time, employee_code]
                )
                print(f"[LOGOUT] Updated most recent login record for employee_code: {employee_code}")
        
        return True

    @staticmethod
    def get_last_login(username):
        """Get the last login time for a user from employee_login_logout_status table."""
        details = AuthService.get_employee_details(username)
        if not details:
            return None
        
        employee_code, _ = details
        
        with connection.cursor() as cursor:
            # Get the most recent login (second most recent if currently logged in)
            # This shows when they last logged in before the current session
            cursor.execute(
                """SELECT last_login FROM employee_login_logout_status 
                   WHERE employee_code = %s AND last_login IS NOT NULL
                   ORDER BY id DESC LIMIT 1 OFFSET 1""",
                [employee_code]
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
            
            # If no previous login, get the current one
            cursor.execute(
                """SELECT last_login FROM employee_login_logout_status 
                   WHERE employee_code = %s AND last_login IS NOT NULL
                   ORDER BY id DESC LIMIT 1""",
                [employee_code]
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
            return None

    @staticmethod
    def validate_employee_code(username, employee_code):
        """Validate that the employee code matches the username."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM employee WHERE name = %s AND code = %s",
                [username, employee_code]
            )
            result = cursor.fetchone()
            return result[0] > 0 if result else False

    @staticmethod
    def get_user_by_employee_code(employee_code):
        """Get user info by employee code"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, password, superuser, status FROM employee WHERE code = %s",
                [employee_code]
            )
            return cursor.fetchone()  # (name, password, superuser, status)
 
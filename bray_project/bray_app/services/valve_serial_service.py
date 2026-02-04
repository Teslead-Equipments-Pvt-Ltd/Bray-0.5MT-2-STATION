"""
Valve Serial Service - Business logic for valve serial number validation and assembly ID operations
"""
from django.db import connection
import pyodbc


class ValveSerialService:
    """Service class for valve serial number operations"""
    
    @staticmethod
    def check_serial_exists(serial_number):
        """
        Check if serial number exists in database
        Returns: True if exists, False otherwise
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT SERIAL_NO FROM abrs_result_status 
                WHERE SERIAL_NO = %s
            """, [serial_number])
            return cursor.fetchone() is not None
    
    @staticmethod
    def get_serial_status(serial_number):
        """
        Get status of a serial number
        Returns: status value or None if not found
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT STATUS FROM abrs_result_status 
                WHERE SERIAL_NO = %s
            """, [serial_number])
            result = cursor.fetchone()
            return result[0] if result else None
    
    @staticmethod
    def get_assembly_number(serial_number):
        """
        Get assembly number for a serial number
        Returns: assembly number or None if not found/empty
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ASSEMBLY_NO FROM abrs_result_status 
                WHERE SERIAL_NO = %s AND ASSEMBLY_NO IS NOT NULL AND ASSEMBLY_NO != ''
            """, [serial_number])
            result = cursor.fetchone()
            if result and result[0]:
                val = str(result[0]).strip()
                if val.lower() in ['null', 'none', 'undefined', '']:
                    return None
                return val
            return None
    
    @staticmethod
    def check_abrs_connection():
        """
        Check if ABRS server is connected and accessible
        Returns: True if connected, False otherwise
        """
        try:
            # Import and use the global abrs_db instance with updated config
            from bray_app.views.api.configuration_api_views import abrs_db, update_abrs_connection
            
            # Ensure ABRS connection is updated with latest config
            update_abrs_connection()
            
            return abrs_db.test_connection()
        except Exception as e:
            print(f"ABRS connection check failed: {str(e)}")
            return False
    
    @staticmethod
    def get_assembly_id_from_abrs(serial_number):
        """
        Get assembly ID from ABRSSample database
        Returns: tuple (assembly_id, error_message)
        """
        try:
            # Import and use the global abrs_db instance with updated config
            from bray_app.views.api.configuration_api_views import abrs_db, update_abrs_connection
            
            # Ensure ABRS connection is updated with latest config
            update_abrs_connection()
            
            with pyodbc.connect(abrs_db.get_connection_string()) as abrs_connection:
                abrs_cursor = abrs_connection.cursor()
                abrs_cursor.execute("""
                    SELECT assemblyId FROM abrsAssembly 
                    WHERE serialNumber = ? 
                """, [serial_number])
                result = abrs_cursor.fetchone()
                
                if result and result[0]:
                    val = str(result[0]).strip()
                    if val.lower() in ['null', 'none', 'undefined', '']:
                        return None, "Invalid/Empty Assembly ID found in ABRS"
                    return val, None
                else:
                    return None, "Serial number not found in ABRS database"
                    
        except pyodbc.Error as e:
            return None, f"ABRS database connection error: {str(e)}"
    
    @staticmethod
    def delete_serial(serial_number):
        """
        Delete existing serial number from abrs_result_status table
        Returns: number of rows deleted
        """
        with connection.cursor() as cursor:
            # cursor.execute("""
            #     DELETE FROM abrs_result_status WHERE SERIAL_NO = %s
            # """, [serial_number])
            cursor.execute("""
                UPDATE abrs_result_status SET STATUS = 0 WHERE SERIAL_NO = %s
            """, [serial_number])
            return cursor.rowcount
    
    @staticmethod
    def check_serial_exists_by_id(serial_number):
        """
        Check if record exists and return its ID
        Returns: tuple (exists, record_id, status) or (False, None, None)
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, STATUS FROM abrs_result_status WHERE SERIAL_NO = %s
            """, [serial_number])
            result = cursor.fetchone()
            
            if result:
                return True, result[0], result[1]
            return False, None, None
    
    @staticmethod
    def insert_serial_with_assembly(serial_number, assembly_id=None):
        """
        Insert new serial number with optional assembly ID
        Status defaults to 0
        """
        with connection.cursor() as cursor:
            if assembly_id:
                cursor.execute("""
                    INSERT INTO abrs_result_status (SERIAL_NO, ASSEMBLY_NO, STATUS) 
                    VALUES (%s, %s, %s)
                """, [serial_number, assembly_id, 0])
            else:
                cursor.execute("""
                    INSERT INTO abrs_result_status (SERIAL_NO, STATUS) 
                    VALUES (%s, %s)
                """, [serial_number, 0])
    
    @staticmethod
    def update_assembly_number(serial_number, assembly_id):
        """
        Update assembly number for existing serial
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE abrs_result_status 
                SET ASSEMBLY_NO = %s 
                WHERE SERIAL_NO = %s
            """, [assembly_id, serial_number])

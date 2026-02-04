from urllib import request
from django.db import connection
from django.shortcuts import redirect
from django.contrib import messages

def getall_testtype():
     with connection.cursor() as cursor:
            cursor.execute("""
                SELECT test_id, test_name, medium, category, status
                FROM test_type
                ORDER BY STATUS DESC, test_id
            """)
            return cursor.fetchall()
        
def get_enabled_categories():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME
            FROM category
            WHERE STATUS = 'ENABLE'
            ORDER BY CATEGORY_NAME
        """)
        return [row[0] for row in cursor.fetchall()]
    
def check_duplicate_testname(testname_lower, test_id):
    with connection.cursor() as cursor:
        # Check for duplicates in database (case-insensitive)
        cursor.execute("""
            SELECT test_id, test_name
            FROM test_type
            WHERE LOWER(test_name) = %s AND test_id != %s
        """, [testname_lower, test_id])
        return cursor.fetchone()
    
def get_columnnames(category):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT PRESSURE_COLUMN_NAME, DURATION_COLUMN_NAME
            FROM category
            WHERE CATEGORY_NAME = %s
        """,
            (category,),
        )
        return cursor.fetchone()
    
def update_testtype( testname,medium,category,status,pressure_column,duration_column,test_id):
    with connection.cursor() as cursor:
        cursor.execute(
                    """
                    UPDATE test_type
                    SET test_name = %s,
                        medium = %s,
                        category = %s,
                        status = %s,
                        pre_col_name = %s,
                        dur_col_name = %s,
                        updated_at = NOW()
                    WHERE test_id = %s
                """,
                    [
                        testname,
                        medium,
                        category,
                        status,
                        pressure_column,
                        duration_column,
                        test_id
                    ],
                )
        return cursor.fetchone()
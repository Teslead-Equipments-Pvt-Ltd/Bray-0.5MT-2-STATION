from django.db import connection, transaction


def get_all_valvesize():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, SIZE_ID, SIZE_NAME, SIZE_DESC, PART_NO, PART_NAME
            FROM valvesize
            ORDER BY SIZE_ID
        """)
       
        return cursor.fetchall()
    

def get_all_valvetype():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TYPE_ID, TYPE_NAME
            FROM valve_type
            ORDER BY TYPE_ID
        """)

        return cursor.fetchall()
    

def get_enabled_categories():

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME, DURATION_COLUMN_NAME
            FROM category
            WHERE STATUS='ENABLE'
            ORDER BY CATEGORY_ID
        """)
        
        return cursor.fetchall()

def delete_multiple_valvesize(size_ids):
    if not size_ids:
        return 0

    placeholders = ",".join(["%s"] * len(size_ids))
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            # Delete related duration data
            cursor.execute(f"DELETE FROM master_duration_data WHERE SIZE_ID IN ({placeholders})", size_ids)
            
            # Delete related degree data
            cursor.execute(f"DELETE FROM master_degree_data WHERE SIZE_ID IN ({placeholders})", size_ids)
            
            # Delete the valve size itself
            cursor.execute(f"DELETE FROM valvesize WHERE SIZE_ID IN ({placeholders})", size_ids)
            
            return cursor.rowcount

    

# def get_all_valvesize():


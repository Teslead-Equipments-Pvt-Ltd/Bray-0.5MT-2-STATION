from django.db import connection

def check_duplicate_category(category_id, testname):
   
    testname_lower = testname.strip().lower()

    with connection.cursor() as cursor:  
        # Check for duplicates in database (case-insensitive)
            cursor.execute("""
                SELECT CATEGORY_ID, CATEGORY_NAME
                FROM category
                WHERE LOWER(CATEGORY_NAME) = %s AND CATEGORY_ID != %s
            """, [testname_lower, category_id])

            duplicate = cursor.fetchone()

    return duplicate is not None


def update_category(category_ids, testnames, statuses):
    
    with connection.cursor() as cursor:
                for category_id, testname, status in zip(category_ids, testnames, statuses):
                    category_id = int(category_id)  # Convert to int
                    cursor.execute("""
                        UPDATE category
                        SET CATEGORY_NAME = %s,
                            STATUS = %s,
                            UPDATED_DATE = NOW()
                        WHERE CATEGORY_ID = %s
                    """, [testname, status, category_id])
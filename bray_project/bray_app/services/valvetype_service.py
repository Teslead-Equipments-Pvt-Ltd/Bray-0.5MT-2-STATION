from django.db import connection

def get_superuser(username):
    with connection.cursor() as cursor:
        cursor.execute("SELECT superuser FROM employee WHERE name = %s", [username])
        return cursor.fetchone()
                        
def get_all_valve_types():
    """Get all valve types with their associated test types"""
    with connection.cursor() as cursor:
        # Fetch all valve types
        cursor.execute("SELECT ID, TYPE_ID, TYPE_NAME, TYPE_DESC FROM valve_type ORDER BY ID")
        rows = cursor.fetchall()
        valve_types = [
            {'id': r[0], 'code': r[1], 'name': r[2], 'description': r[3]} for r in rows
        ]

        # Fetch enabled test types
        cursor.execute("""
            SELECT TEST_ID, TEST_NAME
            FROM test_type
            WHERE STATUS = 'ENABLE'
            ORDER BY TEST_ID
        """)
        test_types = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        # Get existing codes & names for validation
        cursor.execute("SELECT TYPE_ID FROM valve_type")
        existing_codes_raw = [str(r[0]) for r in cursor.fetchall()]
        cursor.execute("SELECT TYPE_NAME FROM valve_type")
        existing_names_raw = [r[0] for r in cursor.fetchall()]

        # Get associated test types for each valve type
        valve_test_types = {}
        for vt in valve_types:
            cursor.execute("SELECT TEST_ID FROM valvetype_testtype WHERE TYPE_ID=%s", [vt['code']])
            selected_tests = [r[0] for r in cursor.fetchall()]
            valve_test_types[vt['code']] = selected_tests

            cursor.execute("""
                SELECT t.TEST_NAME
                FROM test_type t
                INNER JOIN valvetype_testtype vt ON t.TEST_ID = vt.TEST_ID
                WHERE vt.TYPE_ID=%s AND t.STATUS='ENABLE'
            """, [vt['code']])
            vt['associated_test_types'] = [r[0] for r in cursor.fetchall()]
            vt['selected_test_type_ids'] = selected_tests

    return {
        'valve_types': valve_types,
        'test_types': test_types,
        'existing_codes': existing_codes_raw,
        'existing_names': existing_names_raw
    }

def add_valve_type(name, description, test_types):
    """Add a new valve type"""
    try:
        with connection.cursor() as cursor:
            # Generate the next numeric TYPE_ID safely
            cursor.execute("SELECT COALESCE(MAX(TYPE_ID), 0) + 1 FROM valve_type")
            result = cursor.fetchone()
            next_code = int(result[0]) if result and result[0] is not None else 1

            # Prevent duplicates
            cursor.execute("SELECT COUNT(*) FROM valve_type WHERE TYPE_NAME=%s", [name])
            if cursor.fetchone()[0] > 0:
                return {'success': False, 'error': f"Valve Type '{name}' already exists."}

            # Insert valve type
            cursor.execute("""
                INSERT INTO valve_type (TYPE_ID, TYPE_NAME, TYPE_DESC)
                VALUES (%s, %s, %s)
            """, [next_code, name, description])

            # Insert associated test types
            for test_type_id in test_types:
                cursor.execute("""
                    INSERT INTO valvetype_testtype (TYPE_ID, TEST_ID)
                    VALUES (%s, %s)
                """, [next_code, test_type_id])

            # Get the inserted record ID
            cursor.execute("SELECT ID FROM valve_type WHERE TYPE_ID=%s", [next_code])
            inserted_id = cursor.fetchone()[0]

            # Get associated test type names
            cursor.execute("""
                SELECT t.TEST_NAME
                FROM test_type t
                INNER JOIN valvetype_testtype vt ON t.TEST_ID = vt.TEST_ID
                WHERE vt.TYPE_ID=%s AND t.STATUS='ENABLE'
            """, [next_code])
            associated_test_types = [r[0] for r in cursor.fetchall()]

            # Return success with valve type data
            valve_type_data = {
                'id': inserted_id,
                'code': next_code,
                'name': name,
                'description': description,
                'associated_test_types': associated_test_types,
                'selected_test_type_ids': test_types
            }

            return {
                'success': True, 
                'message': f"Valve Type '{name}' added successfully",
                'valve_type': valve_type_data
            }
    except Exception as e:
        return {'success': False, 'error': f'Error adding valve type: {str(e)}'}

def edit_valve_type(valve_id, name, description, test_types):
    """Edit an existing valve type"""
    try:
        with connection.cursor() as cursor:
            # Fetch TYPE_ID from ID
            cursor.execute("SELECT TYPE_ID FROM valve_type WHERE ID=%s", [valve_id])
            fetched = cursor.fetchone()
            if not fetched or not fetched[0]:
                return {'success': False, 'error': "Invalid Valve Type."}
            
            code = fetched[0]

            # Check for duplicate name
            cursor.execute("SELECT COUNT(*) FROM valve_type WHERE TYPE_NAME=%s AND ID!=%s", [name, valve_id])
            if cursor.fetchone()[0] > 0:
                return {'success': False, 'error': f"Valve Type '{name}' already exists."}

            # Update valve_type table
            cursor.execute("""
                UPDATE valve_type
                SET TYPE_NAME=%s, TYPE_DESC=%s
                WHERE ID=%s
            """, [name, description, valve_id])

            # Refresh test type links
            cursor.execute("DELETE FROM valvetype_testtype WHERE TYPE_ID=%s", [code])
            # cursor.execute("Truncate table valvetype_testtype")
            for test_type_id in test_types:
                cursor.execute("""
                    INSERT INTO valvetype_testtype (TYPE_ID, TEST_ID)
                    VALUES (%s, %s)
                """, [code, test_type_id])

            # Get associated test type names
            cursor.execute("""
                SELECT t.TEST_NAME
                FROM test_type t
                INNER JOIN valvetype_testtype vt ON t.TEST_ID = vt.TEST_ID
                WHERE vt.TYPE_ID=%s AND t.STATUS='ENABLE'
            """, [code])
            associated_test_types = [r[0] for r in cursor.fetchall()]

            # Return success with valve type data
            valve_type_data = {
                'id': valve_id,
                'code': code,
                'name': name,
                'description': description,
                'associated_test_types': associated_test_types,
                'selected_test_type_ids': test_types
            }

            return {
                'success': True, 
                'message': f"Valve Type '{name}' updated successfully!",
                'valve_type': valve_type_data
            }
    except Exception as e:
        return {'success': False, 'error': f'Error updating valve type: {str(e)}'}

def delete_valve_type(valve_type_id):
    """Delete a valve type and its associated test type links"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT TYPE_NAME, TYPE_ID FROM valve_type WHERE ID=%s", [valve_type_id])
            result = cursor.fetchone()
            if not result:
                return {'success': False, 'error': "Valve Type not found."}

            valve_type_name, type_code = result
            cursor.execute("DELETE FROM valvetype_testtype WHERE TYPE_ID=%s", [type_code])
            cursor.execute("UPDATE master_degree_data SET TYPE_ID=NULL WHERE TYPE_ID=%s", [type_code])
            cursor.execute("DELETE FROM valve_type WHERE ID=%s", [valve_type_id])

            return {'success': True, 'message': f'Valve Type "{valve_type_name}" deleted successfully!'}
    except Exception as e:
        return {'success': False, 'error': f'Error deleting valve type: {str(e)}'}

def get_valve_type_by_id(valve_id):
    """Get a specific valve type by ID"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ID, TYPE_ID, TYPE_NAME, TYPE_DESC FROM valve_type WHERE ID=%s", [valve_id])
            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'code': result[1], 
                    'name': result[2],
                    'description': result[3]
                }
            return None
    except Exception as e:
        return None

def delete_multiple_valve_types(ids):
    """Delete multiple valve types and their associated test type links"""
    if not ids:
        return 0
        
    try:
        placeholders = ",".join(["%s"] * len(ids))
        with connection.cursor() as cursor:
            # First need to find the TYPE_IDs (codes) for these IDs to delete relationships
            cursor.execute(f"SELECT TYPE_ID FROM valve_type WHERE ID IN ({placeholders})", ids)
            type_codes = [r[0] for r in cursor.fetchall()]
            
            if type_codes:
                code_placeholders = ",".join(["%s"] * len(type_codes))
                cursor.execute(f"DELETE FROM valvetype_testtype WHERE TYPE_ID IN ({code_placeholders})", type_codes)
            
            cursor.execute(f"UPDATE master_degree_data SET TYPE_ID=NULL WHERE TYPE_ID IN ({placeholders})", type_codes)
            cursor.execute(f"DELETE FROM valve_type WHERE ID IN ({placeholders})", ids)
            return cursor.rowcount
    except Exception as e:
        print(f"Error in delete_multiple_valve_types: {e}")
        return 0

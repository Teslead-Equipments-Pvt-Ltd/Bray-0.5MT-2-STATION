"""
ABRS Service - Business logic for ABRS serial number operations
"""
from django.db import connection
import pyodbc


# Column mapping - maps column number to display name
COLUMN_MAPPING = {
    1: 'OPEN TORQUE',
    2: 'CLOSE TORQUE',
    3: 'VALVE CYCLE TEST',
    4: 'HYDRO SHELL TEST RESULT',
    5: 'HYDRO SHELL TEST DURATION',
    6: 'HYDRO SEAT P TEST RESULT',
    7: 'HYDRO SEAT P TEST DURATION',
    8: 'HYDRO SEAT N TEST RESULT',
    9: 'HYDRO SEAT N TEST DURATION',
    10: 'AIR SEAT P TEST RESULT',
    11: 'AIR SEAT P TEST DURATION',
    12: 'AIR SEAT N TEST RESULT',
    13: 'AIR SEAT N TEST DURATION',
}


def get_abrs_connection():
    """
    Get ABRS database connection using the same method as configuration API.
    Uses the global abrs_db instance from configuration_api_views.
    
    Returns:
        pyodbc.Connection: ABRS database connection
        
    Raises:
        pyodbc.Error: If connection fails
        ValueError: If configuration is missing
    """
    from bray_app.views.api.configuration_api_views import abrs_db, update_abrs_connection
    
    # Update connection configuration if needed
    update_abrs_connection()
    
    # Check if configuration is available
    if not abrs_db.server or not abrs_db.database:
        raise ValueError("ABRS server and database must be configured")
    
    # Use the same connection string method as configuration API
    conn_str = abrs_db.get_connection_string()
    return pyodbc.connect(conn_str)


class ABRSService:
    """Service class for ABRS operations"""
    
    @staticmethod
    def get_status_display(status_code):
        """
        Convert status code to display text and badge class.
        
        Args:
            status_code: Integer status (0-3)
            
        Returns:
            dict: {'text': str, 'class': str}
        """
        status_map = {
            0: {'text': 'Not Performed', 'class': 'pending'},
            1: {'text': 'Running', 'class': 'running'},
            2: {'text': 'Test Performed', 'class': 'pass'},
            3: {'text': 'Test Performed & Pushed', 'class': 'pushed'}
        }
        
        # Default to 0 if invalid status
        try:
            code = int(status_code) if status_code is not None else 0
            return status_map.get(code, status_map[0])
        except (ValueError, TypeError):
            return status_map[0]
    
    @staticmethod
    def get_table_data():
        """
        Fetch ABRS table data with column headers and values.
        
        Returns:
            dict: {
                'column_headers': [...],
                'data': [...]
            }
        """
        abrs_data = []
        
        # Use predefined column headers from mapping
        column_headers = [COLUMN_MAPPING.get(i, f'COL{i}') for i in range(1, 14)]
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO, STATUS,
                           COL1_VALUE, COL2_VALUE, COL3_VALUE, COL4_VALUE, COL5_VALUE,
                           COL6_VALUE, COL7_VALUE, COL8_VALUE, COL9_VALUE, COL10_VALUE,
                           COL11_VALUE, COL12_VALUE, COL13_VALUE, PUSHED_COLUMNS
                    FROM abrs_result_status
                    ORDER BY id DESC
                """)
                rows = cursor.fetchall()
                
                # Process data rows
                for idx, row in enumerate(rows, 1):
                    status_code = row[2]
                    status_info = ABRSService.get_status_display(status_code)
                    
                    # Parse pushed columns (comma-separated string like "0,1,2,3")
                    pushed_columns = []
                    if row[16]:  # PUSHED_COLUMNS field
                        try:
                            pushed_columns = [int(x) for x in row[16].split(',') if x.strip()]
                        except:
                            pushed_columns = []
                    
                    row_data = {
                        'sno': idx,
                        'serial_no': row[0] or '',
                        'assembly_no': row[1] or '',
                        'status_code': status_code if status_code is not None else 0,
                        'status_text': status_info['text'],
                        'status_class': status_info['class'],
                        'col_values': [row[i] if row[i] else '-' for i in range(3, 16)],
                        'pushed_columns': pushed_columns  # Array of column indices that were pushed
                    }
                    abrs_data.append(row_data)
                    
        except Exception as e:
            print(f"Error fetching ABRS data: {e}")
        
        return {
            'column_headers': column_headers,
            'data': abrs_data
        }
    
    @staticmethod
    def search_serials(query):
        """
        Search serial numbers for autocomplete.
        
        Args:
            query: Search string
            
        Returns:
            list: List of matching serials
        """
        serials = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO 
                    FROM abrs_result_status 
                    WHERE SERIAL_NO LIKE %s
                    LIMIT 10
                """, [f'%{query}%'])
                rows = cursor.fetchall()
                
                for row in rows:
                    serials.append({
                        'number': row[0],
                        'displayType': row[1] or 'N/A'
                    })
        except Exception as e:
            print(f"Error searching serials: {e}")
        
        return serials
    
    @staticmethod
    def get_serial_details(serial_number):
        """
        Get details for a specific serial number.
        
        Args:
            serial_number: The serial number to look up
            
        Returns:
            dict or None: Serial details if found
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO, STATUS,
                           COL1_NAME, COL2_NAME, COL3_NAME, COL4_NAME, COL5_NAME,
                           COL6_NAME, COL7_NAME, COL8_NAME, COL9_NAME, COL10_NAME,
                           COL11_NAME, COL12_NAME, COL13_NAME,
                           COL1_VALUE, COL2_VALUE, COL3_VALUE, COL4_VALUE, COL5_VALUE,
                           COL6_VALUE, COL7_VALUE, COL8_VALUE, COL9_VALUE, COL10_VALUE,
                           COL11_VALUE, COL12_VALUE, COL13_VALUE
                    FROM abrs_result_status
                    WHERE SERIAL_NO = %s
                """, [serial_number])
                row = cursor.fetchone()
                
                if row:
                    return {
                        'serial_no': row[0],
                        'assembly_no': row[1],
                        'status': row[2],
                        'columns': {
                            f'col{i-2}': {'name': row[i], 'value': row[i+13]} 
                            for i in range(3, 16)
                        }
                    }
        except Exception as e:
            print(f"Error getting serial details: {e}")
        
        return None
    
    @staticmethod
    def import_serial_from_abrs(serial_number):
        """
        Import serial from ABRS database and add/update local database.
        New logic:
        - Check for duplicates by Assembly ID (not Serial Number)
        - If Serial Number exists but Assembly ID is missing → Update successfully
        - If both Serial Number AND Assembly ID already exist → Show error (duplicate)
        
        Args:
            serial_number: The serial number to import
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Connect to ABRS database using common function
            abrs_conn = get_abrs_connection()
            abrs_cursor = abrs_conn.cursor()
            
            # Query ABRS database for serial number
            abrs_cursor.execute("""
                SELECT serialNumber, assemblyId 
                FROM abrsAssembly 
                WHERE serialNumber = ?
            """, [serial_number])
            
            row = abrs_cursor.fetchone()
            abrs_cursor.close()
            abrs_conn.close()
            
            if not row:
                return {
                    'success': False,
                    'message': f'Serial number {serial_number} not found in ABRS database'
                }
            
            serial_no = row[0]
            assembly_id = row[1]
            
            # Check existing records in local database
            with connection.cursor() as cursor:
                # Check if serial exists
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO FROM abrs_result_status 
                    WHERE SERIAL_NO = %s
                """, [serial_no])
                
                existing_serial_record = cursor.fetchone()
                
                # Check if assembly ID already exists (duplicate check by assembly)
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO FROM abrs_result_status 
                    WHERE ASSEMBLY_NO = %s AND ASSEMBLY_NO IS NOT NULL AND ASSEMBLY_NO != ''
                """, [assembly_id])
                
                existing_assembly_record = cursor.fetchone()
                
                if existing_serial_record:
                    existing_assembly_no = existing_serial_record[1]
                    
                    # Case 1: Serial exists but Assembly ID is missing/empty → Update successfully
                    if not existing_assembly_no or existing_assembly_no.strip() == '' or existing_assembly_no == '-':
                        cursor.execute("""
                            UPDATE abrs_result_status 
                            SET ASSEMBLY_NO = %s
                            WHERE SERIAL_NO = %s
                        """, [assembly_id, serial_no])
                        
                        return {
                            'success': True,
                            'message': f'Serial {serial_no} updated successfully with Assembly {assembly_id}',
                            'serial_no': serial_no,
                            'assembly_no': assembly_id,
                            'action': 'updated'
                        }
                    
                    # Case 2: Both Serial Number AND Assembly ID already exist → Error (duplicate)
                    elif existing_assembly_no == assembly_id:
                        return {
                            'success': False,
                            'message': f'Duplicate record: Serial {serial_no} with Assembly {assembly_id} already exists in database',
                            'serial_no': serial_no,
                            'assembly_no': assembly_id
                        }
                    
                    # Case 3: Serial exists with different Assembly ID → Error (conflict)
                    else:
                        return {
                            'success': False,
                            'message': f'Conflict: Serial {serial_no} already exists with different Assembly {existing_assembly_no}. Cannot update to {assembly_id}',
                            'serial_no': serial_no,
                            'assembly_no': existing_assembly_no
                        }
                
                # Case 4: Check if Assembly ID exists with different serial (duplicate assembly check)
                elif existing_assembly_record:
                    existing_serial_no = existing_assembly_record[0]
                    return {
                        'success': False,
                        'message': f'Duplicate Assembly ID: Assembly {assembly_id} already exists with Serial {existing_serial_no}',
                        'serial_no': existing_serial_no,
                        'assembly_no': assembly_id
                    }
                
                # Case 5: Neither serial nor assembly exists → Insert new record
                else:
                    cursor.execute("""
                        INSERT INTO abrs_result_status 
                        (SERIAL_NO, ASSEMBLY_NO, STATUS)
                        VALUES (%s, %s, 0)
                    """, [serial_no, assembly_id])
                    
                    return {
                        'success': True,
                        'message': f'Serial {serial_no} imported successfully with Assembly {assembly_id}',
                        'serial_no': serial_no,
                        'assembly_no': assembly_id,
                        'action': 'inserted'
                    }
            
        except pyodbc.Error as e:
            return {
                'success': False,
                'message': f'ABRS database connection error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error importing serial: {str(e)}'
            }
    
    @staticmethod
    def sync_serials_by_date_range(from_date, to_date):
        """
        Sync serials from ABRS by date range.
        
        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            dict: Result with success status and message
        """
        from datetime import datetime
        
        try:
            # Validate dates
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            
            if from_dt > to_dt:
                return {
                    'success': False,
                    'message': 'From date cannot be after To date'
                }
            
            # Connect to ABRS database using common function
            abrs_conn = get_abrs_connection()
            abrs_cursor = abrs_conn.cursor()
            
            # Query ABRS database for serials in date range
            abrs_cursor.execute("""
                SELECT serialNumber, assemblyId 
                FROM abrsAssembly 
                WHERE CAST(CreateDate AS DATE) BETWEEN ? AND ?
            """, [from_date, to_date])
            
            rows = abrs_cursor.fetchall()
            abrs_cursor.close()
            abrs_conn.close()
            
            if not rows:
                return {
                    'success': False,
                    'message': f'No records found between {from_date} and {to_date}'
                }
            
            # Check for duplicates and separate new serials
            new_serials = []
            skipped_serials = []
            
            with connection.cursor() as cursor:
                for row in rows:
                    serial_no = row[0]
                    assembly_id = row[1]
                    
                    # Check if serial already exists
                    cursor.execute("""
                        SELECT SERIAL_NO, ASSEMBLY_NO FROM abrs_result_status 
                        WHERE SERIAL_NO = %s
                    """, [serial_no])
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Skip duplicate - don't update
                        skipped_serials.append({
                            'serial': serial_no,
                            'assembly': existing[1]
                        })
                    else:
                        # New serial - will be inserted
                        new_serials.append({
                            'serial': serial_no,
                            'assembly': assembly_id
                        })
            
            # Insert only new serials (skip duplicates) with STATUS = 0 (Not Performed)
            imported_count = 0
            with connection.cursor() as cursor:
                for item in new_serials:
                    cursor.execute("""
                        INSERT INTO abrs_result_status 
                        (SERIAL_NO, ASSEMBLY_NO, STATUS)
                        VALUES (%s, %s, 0)
                    """, [item['serial'], item['assembly']])
                    imported_count += 1
            
            # Build message
            if skipped_serials:
                message = f'Imported {imported_count} new record(s), skipped {len(skipped_serials)} duplicate(s)'
            else:
                message = f'Successfully imported {imported_count} new record(s)'
            
            return {
                'success': True,
                'message': message,
                'imported_count': imported_count,
                'skipped_count': len(skipped_serials),
                'total_scanned': len(rows),
                'serials': new_serials,
                'skipped_serials': skipped_serials
            }
            
        except pyodbc.Error as e:
            return {
                'success': False,
                'message': f'ABRS database error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error syncing serials: {str(e)}'
            }
    
    @staticmethod
    def sync_serials_by_date(date):
        """
        Sync serials from ABRS by single date.
        
        Args:
            date: The date to sync
            
        Returns:
            dict: Result with success status and message
        """
        # TODO: Implement ABRS sync logic
        return {
            'success': True,
            'message': f'Synced serials for {date}',
            'updated_count': 0,
            'total_scanned': 0,
            'serials': []
        }
    
    @staticmethod
    def update_status(serial_no, status_code):
        """
        Update the status of a serial number.
        
        Args:
            serial_no: Serial number to update
            status_code: New status code (0-3)
                0 = Not Performed
                1 = Running
                2 = Test Performed
                3 = Test Performed & Pushed
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Validate status code
            if status_code not in [0, 1, 2, 3]:
                return {
                    'success': False,
                    'message': f'Invalid status code: {status_code}. Must be 0-3.'
                }
            
            with connection.cursor() as cursor:
                # Check if serial exists
                cursor.execute("""
                    SELECT COUNT(*) FROM abrs_result_status 
                    WHERE SERIAL_NO = %s
                """, [serial_no])
                
                exists = cursor.fetchone()[0] > 0
                
                if not exists:
                    return {
                        'success': False,
                        'message': f'Serial number {serial_no} not found'
                    }
                
                # Update status
                cursor.execute("""
                    UPDATE abrs_result_status 
                    SET STATUS = %s
                    WHERE SERIAL_NO = %s
                """, [status_code, serial_no])
                
                status_info = ABRSService.get_status_display(status_code)
                
                return {
                    'success': True,
                    'message': f'Status updated to: {status_info["text"]}',
                    'serial_no': serial_no,
                    'status_code': status_code,
                    'status_text': status_info['text']
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating status: {str(e)}'
            }
    
    @staticmethod
    def get_assembly_from_abrs(serial_no):
        """
        Get assembly ID from ABRS database based on serial number and update local database.
        
        Args:
            serial_no: Serial number to look up
            
        Returns:
            dict: Result with success status, message, and assembly_no
        """
        try:
            # Check if serial exists in local database
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO FROM abrs_result_status 
                    WHERE SERIAL_NO = %s
                """, [serial_no])
                
                local_record = cursor.fetchone()
                
                if not local_record:
                    return {
                        'success': False,
                        'message': f'Serial number {serial_no} not found in local database'
                    }
            
            # Connect to ABRS database using common function
            abrs_conn = get_abrs_connection()
            abrs_cursor = abrs_conn.cursor()
            
            # Query ABRS database for assembly ID based on serial number
            abrs_cursor.execute("""
                SELECT serialNumber, assemblyId 
                FROM abrsAssembly 
                WHERE serialNumber = ?
            """, [serial_no])
            
            row = abrs_cursor.fetchone()
            abrs_cursor.close()
            abrs_conn.close()
            
            if not row:
                return {
                    'success': False,
                    'message': f'Serial number {serial_no} not found in ABRS database'
                }
            
            assembly_id = row[1]
            
            # Update local database with assembly ID
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE abrs_result_status 
                    SET ASSEMBLY_NO = %s
                    WHERE SERIAL_NO = %s
                """, [assembly_id, serial_no])
            
            return {
                'success': True,
                'message': f'Assembly ID retrieved and updated successfully',
                'serial_no': serial_no,
                'assembly_no': assembly_id
            }
            
        except pyodbc.Error as e:
            return {
                'success': False,
                'message': f'ABRS database error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting assembly: {str(e)}'
            }
    
    @staticmethod
    def push_data_to_abrs(serial_no, assembly_no):
        """
        Push test data from local database to ABRS database.
        Reads 13 column values from local database and inserts them into ABRS database
        based on assembly_id and test_id mapping.
        
        Args:
            serial_no: Serial number
            assembly_no: Assembly number
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Get test data from local database
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SERIAL_NO, ASSEMBLY_NO, STATUS,
                           COL1_VALUE, COL2_VALUE, COL3_VALUE, COL4_VALUE, COL5_VALUE,
                           COL6_VALUE, COL7_VALUE, COL8_VALUE, COL9_VALUE, COL10_VALUE,
                           COL11_VALUE, COL12_VALUE, COL13_VALUE
                    FROM abrs_result_status
                    WHERE SERIAL_NO = %s AND ASSEMBLY_NO = %s
                """, [serial_no, assembly_no])
                
                row = cursor.fetchone()
                
                if not row:
                    return {
                        'success': False,
                        'message': f'Serial {serial_no} with Assembly {assembly_no} not found in local database'
                    }
                
                # Extract column values (indices 3-15 are COL1_VALUE to COL13_VALUE)
                test_values = {
                    'col1': row[3],   # Open Torque - Test ID 9
                    'col2': row[4],   # Close Torque - Test ID 7
                    'col3': row[5],   # Valve Cycle Test - Test ID 2
                    'col4': row[6],   # Hydro Shell Test Result - Test ID 11
                    'col5': row[7],   # Hydro Shell Test Duration - Test ID 12
                    'col6': row[8],   # Hydro Seat P Test Result - Test ID 35
                    'col7': row[9],   # Hydro Seat P Test Duration - Test ID 36
                    'col8': row[10],  # Hydro Seat N Test Result - Test ID 31
                    'col9': row[11],  # Hydro Seat N Test Duration - Test ID 32
                    'col10': row[12], # Air Seat P Test Result - Test ID 19
                    'col11': row[13], # Air Seat P Test Duration - Test ID 20
                    'col12': row[14], # Air Seat N Test Result - Test ID 15
                    'col13': row[15], # Air Seat N Test Duration - Test ID 16
                }
            
            # Test ID mapping based on the image provided
            test_id_mapping = {
                'col1': 9,   # Open Torque
                'col2': 7,   # Close Torque
                'col3': 2,   # Valve Cycle Test
                'col4': 11,  # Hydro Shell Test Result
                'col5': 12,  # Hydro Shell Test Duration
                'col6': 35,  # Hydro Seat P Test Result
                'col7': 36,  # Hydro Seat P Test Duration
                'col8': 31,  # Hydro Seat N Test Result
                'col9': 32,  # Hydro Seat N Test Duration
                'col10': 19, # Air Seat P Test Result
                'col11': 20, # Air Seat P Test Duration
                'col12': 15, # Air Seat N Test Result
                'col13': 16, # Air Seat N Test Duration
            }
            
            # Connect to ABRS database using common function
            abrs_conn = get_abrs_connection()
            abrs_cursor = abrs_conn.cursor()
            
            # Push data for each test parameter (13 separate queries)
            success_count = 0
            failed_tests = []
            skipped_count = 0
            pushed_columns = []  # Track which columns were successfully pushed
            pushed_results = 0  # Track pressure test results pushed
            pushed_durations = 0  # Track duration values pushed
            
            for col_key, test_id in test_id_mapping.items():
                test_value = test_values.get(col_key)
                
                # Skip if value is None or empty
                if test_value is None or test_value == '' or test_value == '-':
                    skipped_count += 1
                    print(f"Skipping {col_key} (Test ID {test_id}): value is empty/null")
                    continue
                
                try:
                    print(f"Processing {col_key} (Test ID {test_id}): value = {test_value}")
                    
                    # Check if record already exists
                    abrs_cursor.execute("""
                        SELECT COUNT(*) FROM abrsAssemblyTest 
                        WHERE assemblyId = ? AND testDetailId = ?
                    """, [assembly_no, test_id])
                    
                    exists = abrs_cursor.fetchone()[0] > 0
                    
                    if exists:
                        # Update existing record only
                        print(f"Updating existing record for Test ID {test_id}")
                        abrs_cursor.execute("""
                            UPDATE abrsAssemblyTest 
                            SET testValue = ?, updatedBy = 'Teslead-100MT', updatedDate = GETDATE()
                            WHERE assemblyId = ? AND testDetailId = ?
                        """, [test_value, assembly_no, test_id])
                        success_count += 1
                        col_index = int(col_key.replace('col', '')) - 1
                        pushed_columns.append(col_index)
                         # Count results vs durations
                        # COL4, COL6, COL8, COL10, COL12 are test results (even indices from 4)
                        # COL5, COL7, COL9, COL11, COL13 are durations (odd indices from 5)
                        if col_key in ['col4', 'col6', 'col8', 'col10', 'col12']:
                            pushed_results += 1
                        elif col_key in ['col5', 'col7', 'col9', 'col11', 'col13']:
                            pushed_durations += 1
                        print(f"Successfully updated {col_key}")
                    else:
                        # Skip if row doesn't exist
                        print(f"Skipping {col_key} (Test ID {test_id}): row doesn't exist in ABRS")
                        skipped_count += 1
                    
                except Exception as e:
                    print(f"Error processing {col_key} (Test ID {test_id}): {str(e)}")
                    failed_tests.append({
                        'test_id': test_id,
                        'column': col_key,
                        'error': str(e)
                    })
            
            # Commit all changes
            abrs_conn.commit()
            abrs_cursor.close()
            abrs_conn.close()
            
            # Store pushed columns information in database as comma-separated string
            if success_count > 0:
                pushed_cols_str = ','.join(map(str, pushed_columns))
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE abrs_result_status 
                        SET PUSHED_COLUMNS = %s
                        WHERE SERIAL_NO = %s AND ASSEMBLY_NO = %s
                    """, [pushed_cols_str, serial_no, assembly_no])
            
            print(f"Summary: Success={success_count}, Failed={len(failed_tests)}, Skipped={skipped_count}, Pushed columns: {pushed_columns}, Results={pushed_results}, Durations={pushed_durations}")
            
            if failed_tests:
                # Return detailed error information
                error_details = "\n".join([f"Test ID {t['test_id']} ({t['column']}): {t['error']}" for t in failed_tests[:3]])
                return {
                    'success': False,
                    'message': f'Pushed {success_count} test(s), but {len(failed_tests)} failed. First errors: {error_details}',
                    'success_count': success_count,
                    'pushed_results': pushed_results,
                    'pushed_durations': pushed_durations,
                    'failed_tests': failed_tests
                }
            
            if success_count == 0:
                return {
                    'success': False,
                    'message': f'No data to push. All {skipped_count} values are empty or null. Please complete the tests first.',
                    'success_count': 0,
                    'pushed_results': 0,
                    'pushed_durations': 0,
                    'failed_tests': []
                }
            
             # Build detailed success message
            message_parts = []
            if pushed_results > 0:
                message_parts.append(f'{pushed_results} test result(s)')
            if pushed_durations > 0:
                message_parts.append(f'{pushed_durations} duration(s)')
            
            detailed_message = f'Successfully pushed {" and ".join(message_parts)} to ABRS'
            
            return {
                'success': True,
                'message': f'Successfully pushed {success_count} test values to ABRS database',
                'success_count': success_count,
                'pushed_results': pushed_results,
                'pushed_durations': pushed_durations
            }
            
        except pyodbc.Error as e:
            return {
                'success': False,
                'message': f'ABRS database error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error pushing data: {str(e)}'
            }

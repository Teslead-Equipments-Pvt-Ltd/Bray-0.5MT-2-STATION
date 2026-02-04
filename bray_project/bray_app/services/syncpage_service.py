from django.db import connection, transaction, IntegrityError
from django.http import JsonResponse




def save_test_pressure_station1(id, name, valve_serial_no, station_data1, final_data_1, cursor):

    try:
        print(f"[SAVE_S1] Starting save for TEST_ID={id}, VALVE_SER_NO={valve_serial_no}")
        
        parameters = final_data_1.get("PARAMETERS", {})

       
        # #Check existing latest record for this valve
        
        # cursor.execute("""
        #     SELECT COUNT_ID, CYCLE_COMPLETE
        #     FROM pressure_analysis
        #     WHERE TEST_ID = %s AND VALVE_SER_NO = %s
        #     ORDER BY COUNT_ID DESC
        #     LIMIT 1
        # """, [id, valve_serial_no])

        # row = cursor.fetchone()

        # if row:
        #     last_count, cycle_complete = row
        #     print(f"[SAVE_S1] Found existing record: COUNT_ID={last_count}, CYCLE_COMPLETE={cycle_complete}")

        #     if cycle_complete == "Yes":
        #         # New cycle → NEW ROW
        #         count = last_count + 1
        #         insert_new = True
        #         print(f"[SAVE_S1] Previous cycle complete, creating new record with COUNT_ID={count}")
        #     else:
        #         # Continue same cycle → UPDATE
        #         count = last_count
        #         insert_new = False
        #         print(f"[SAVE_S1] Continuing existing cycle, updating COUNT_ID={count}")
        # else:
        #     # First time valve
        #     count = 1
        #     insert_new = True
        #     print(f"[SAVE_S1] First time for this valve, creating COUNT_ID={count}")

        default_count = 1
        count = 0
        cursor.execute("""
            select Count_No from serial_tbl where Serial_No = %s
            """, [valve_serial_no])
        row = cursor.fetchone()

        if row is None:
            serial_count = None   
        else:
            serial_count = row[0]
        
        if serial_count:
            cursor.execute("""
                SELECT CYCLE_COMPLETE
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s AND COUNT_ID = %s
                ORDER BY COUNT_ID DESC
                LIMIT 1
            """, [valve_serial_no, serial_count])
            row = cursor.fetchone()
            if row:
                cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
                        """,[valve_serial_no, id])
                row2 = cursor.fetchone()
                if row2:
                    insert_new = False
                else:
                    count = serial_count + 1
                    insert_new = True
            else:
                # No existing record in pressure_analysis, check temp table
                cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
                        """,[valve_serial_no, id])
                row2 = cursor.fetchone()
                if row2:
                    insert_new = False
                else:
                    count = serial_count + 1
                    insert_new = True
        else:
            # Continue same cycle → UPDATE
            cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
                        """,[valve_serial_no, id])
            row2 = cursor.fetchone()
            if row2:
                insert_new = False
            else:
                count = default_count
                insert_new = True

       
        #Common columns
        
        columns = [
            "TEST_ID",
            "TEST_NAME",
            "VALVE_SER_NO",
            "COUNT_ID",
            "CYCLE_COMPLETE",
            "SET_PRESSURE",
            "PRESSURE_UNIT",
            "SET_TIME",
            "SET_TIME_UNIT",
            "STANDARD_NAME",
            "VALVESIZE_NAME",
            "VALVETYPE_NAME",
            "VALVECLASS_NAME",
            "SHELLMATERIAL_NAME"
        ]

        values = ["%s"] * len(columns)

        data = [
            id,
            name,
            valve_serial_no,
            count,
            "No",   # default cycle status
            station_data1.get("TESTING_PRESSURE"),
            station_data1.get("TESTING_PSR_UNIT"),
            station_data1.get("TESTING_DUR"),
            station_data1.get("TESTING_DUR_UNIT"),
            final_data_1.get("STANDARD_NAME"),
            final_data_1.get("SIZE_NAME"),
            final_data_1.get("TYPE_NAME"),
            final_data_1.get("CLASS_NAME"),
            final_data_1.get("SHELL_MATERIAL_NAME")
        ]

        # Dynamic parameter columns
        
        index = 1
        for param_name, param_value in parameters.items():
            if index > 23:
                break

            columns.extend([f"COL{index}_NAME", f"COL{index}_VALUE"])
            values.extend(["%s", "%s"])
            data.extend([param_name, param_value])
            index += 1

        # INSERT or UPDATE logic
       

        tables = ["temp_pressure_analysis", "pressure_analysis"]

        with transaction.atomic():
            for table in tables:

                if insert_new:
                    sql = f"""
                        INSERT INTO {table}
                        ({', '.join(columns)})
                        VALUES ({', '.join(values)})
                    """
                    print(f"[SAVE_S1] Inserting into {table}")
                    cursor.execute(sql, data)
                    print(f"[SAVE_S1] Successfully inserted into {table}")

                else:
                    # fields to update (exclude keys)
                    update_fields = [f"{col} = %s" for col in columns[5:]]

                    sql = f"""
                        UPDATE {table}
                        SET {', '.join(update_fields)}
                        WHERE TEST_ID = %s AND VALVE_SER_NO = %s AND COUNT_ID = %s
                    """

                    #build correct update data
                    update_data = (
                        data[5:] +        # values for SET columns
                        [id, valve_serial_no, count]  # WHERE values
                    )

                    print(f"[SAVE_S1] Updating {table}")
                    cursor.execute(sql, update_data)
                    print(f"[SAVE_S1] Successfully updated {table}")
        
        print(f"[SAVE_S1] All operations completed successfully")
        
    except Exception as e:
        print(f"[SAVE_S1] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise



def save_test_pressure_station2(id, name, valve_serial_no, station_data2, final_data_2, cursor):

    try:
        print(f"[SAVE_S2] Starting save for TEST_ID={id}, VALVE_SER_NO={valve_serial_no}")
        
        parameters = final_data_2.get("PARAMETERS", {})

       
        #Check existing latest record for this valve
        
        # cursor.execute("""
        #     SELECT COUNT_ID, CYCLE_COMPLETE
        #     FROM pressure_analysis
        #     WHERE TEST_ID = %s AND VALVE_SER_NO = %s
        #     ORDER BY COUNT_ID DESC
        #     LIMIT 1
        # """, [id, valve_serial_no])

        # row = cursor.fetchone()

        # if row:
        #     last_count, cycle_complete = row
        #     print(f"[SAVE_S2] Found existing record: COUNT_ID={last_count}, CYCLE_COMPLETE={cycle_complete}")

        #     if cycle_complete == "Yes":
        #         # New cycle → NEW ROW
        #         count = last_count + 1
        #         insert_new = True
        #         print(f"[SAVE_S2] Previous cycle complete, creating new record with COUNT_ID={count}")
        #     else:
        #         # Continue same cycle → UPDATE
        #         count = last_count
        #         insert_new = False
        #         print(f"[SAVE_S2] Continuing existing cycle, updating COUNT_ID={count}")
        # else:
        #     # First time valve
        #     count = 1
        #     insert_new = True
        #     print(f"[SAVE_S2] First time for this valve, creating COUNT_ID={count}")

        default_count = 1   
        count = 0
        cursor.execute("""
            select Count_No from serial_tbl where Serial_No = %s
            """, [valve_serial_no])
        row = cursor.fetchone()

        if row is None:
            serial_count = None  
        else:
            serial_count = row[0]
        
        if serial_count:
            cursor.execute("""
                SELECT CYCLE_COMPLETE
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s AND COUNT_ID = %s
                ORDER BY COUNT_ID DESC
                LIMIT 1
            """, [valve_serial_no, serial_count])
            row = cursor.fetchone()
            if row:
                cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
                        """,[valve_serial_no, id])
                row2 = cursor.fetchone()
                if row2:
                    insert_new = False
                else:
                    count = serial_count + 1
                    insert_new = True
            else:
                # No existing record in pressure_analysis, check temp table
                cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
                        """,[valve_serial_no, id])
                row2 = cursor.fetchone()
                if row2:
                    insert_new = False
                else:
                    count = serial_count + 1
                    insert_new = True
        else:
            # Continue same cycle → UPDATE
            cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
                        """,[valve_serial_no, id])
            row2 = cursor.fetchone()
            if row2:
                insert_new = False
            else:
                count = default_count
                insert_new = True

       
        #Common columns
        
        columns = [
            "TEST_ID",
            "TEST_NAME",
            "VALVE_SER_NO",
            "COUNT_ID",
            "CYCLE_COMPLETE",
            "SET_PRESSURE",
            "PRESSURE_UNIT",
            "SET_TIME",
            "SET_TIME_UNIT",
            "STANDARD_NAME",
            "VALVESIZE_NAME",
            "VALVETYPE_NAME",
            "VALVECLASS_NAME",
            "SHELLMATERIAL_NAME"
        ]

        values = ["%s"] * len(columns)

        data = [
            id,
            name,
            valve_serial_no,
            count,
            "No",   # default cycle status
            station_data2.get("TESTING_PRESSURE"),
            station_data2.get("TESTING_PSR_UNIT"),
            station_data2.get("TESTING_DUR"),
            station_data2.get("TESTING_DUR_UNIT"),
            final_data_2.get("STANDARD_NAME"),
            final_data_2.get("SIZE_NAME"),
            final_data_2.get("TYPE_NAME"),
            final_data_2.get("CLASS_NAME"),
            final_data_2.get("SHELL_MATERIAL_NAME")
        ]

        # Dynamic parameter columns
        
        index = 1
        for param_name, param_value in parameters.items():
            if index > 23:
                break

            columns.extend([f"COL{index}_NAME", f"COL{index}_VALUE"])
            values.extend(["%s", "%s"])
            data.extend([param_name, param_value])
            index += 1

        # INSERT or UPDATE logic
       

        tables = ["temp_pressure_analysis", "pressure_analysis"]

        with transaction.atomic():
            for table in tables:

                if insert_new:
                    sql = f"""
                        INSERT INTO {table}
                        ({', '.join(columns)})
                        VALUES ({', '.join(values)})
                    """
                    print(f"[SAVE_S2] Inserting into {table}")
                    cursor.execute(sql, data)
                    print(f"[SAVE_S2] Successfully inserted into {table}")

                else:
                    # fields to update (exclude keys)
                    update_fields = [f"{col} = %s" for col in columns[5:]]

                    sql = f"""
                        UPDATE {table}
                        SET {', '.join(update_fields)}
                        WHERE TEST_ID = %s AND VALVE_SER_NO = %s AND COUNT_ID = %s
                    """

                    #build correct update data
                    update_data = (
                        data[5:] +        # values for SET columns
                        [id, valve_serial_no, count]  # WHERE values
                    )

                    print(f"[SAVE_S2] Updating {table}")
                    cursor.execute(sql, update_data)
                    print(f"[SAVE_S2] Successfully updated {table}")
        
        print(f"[SAVE_S2] All operations completed successfully")
        
    except Exception as e:
        print(f"[SAVE_S2] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


def save_valve_serial_no(valve_serial_no):
    with transaction.atomic():
        with connection.cursor() as cursor:
            # Check if valve serial number already exists
            cursor.execute("""
                SELECT Serial_No FROM serial_tbl WHERE Serial_No = %s
            """, [valve_serial_no])
            
            row = cursor.fetchone()
            
            if row:
                 # Update (Increment)
                cursor.execute("""
                    UPDATE serial_tbl 
                    SET Count_No = Count_No + 1 
                    WHERE Serial_No = %s
                """, [valve_serial_no])
                print(f"Incremented cycle count for valve serial number: {valve_serial_no}")

            else:
                 # Insert new
                cursor.execute("""
                    INSERT INTO serial_tbl (Serial_No, Count_No)
                    VALUES (%s, %s)
                """, [valve_serial_no, 1])
                print(f"Inserted new valve serial number: {valve_serial_no}")



def clear_temp_pressure_analysis(valve_serial_no):
     with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
                """, [valve_serial_no])


def cycle_complete_status(valve_ser_no):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE pressure_analysis
                SET CYCLE_COMPLETE = 'Yes'
                WHERE VALVE_SER_NO = %s
                        """, [valve_ser_no])


def clear_testing_dataS1(valve_serial_no):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""
                    DELETE FROM temp_testing_data_s1
                    WHERE VALVE_SERIAL_NO = %s
                """, [valve_serial_no])


def clear_testing_dataS2(valve_serial_no):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""
                    DELETE FROM temp_testing_data_s2
                    WHERE VALVE_SERIAL_NO = %s
                """, [valve_serial_no])


def disable_sync_station1():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""UPDATE master_temp_data SET STATION_STATUS = 'Disabled' WHERE ID = 1""")

def disable_sync_station2():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""UPDATE master_temp_data SET STATION_STATUS = 'Disabled' WHERE ID = 2""")
                            

def clear_station_1():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE current_status_station1")


def clear_station_2():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE current_status_station2")


def update_tested_values_service(station_num, test_id, valve_serial_no, test_data):
    """
    Service function to update tested values in both temp_pressure_analysis and pressure_analysis tables.
    
    Args:
        station_num: Station number (1 or 2)
        test_id: Test ID
        valve_serial_no: Valve serial number
        test_data: Dictionary containing test values with keys:
            - start_pressure: Starting pressure value
            - end_pressure: Ending pressure value
            - start_time: Test start time
            - end_time: Test end time
            - result_psr: Result pressure
            - actual_time: Actual test duration
            - clamping_psr: Clamping pressure
            - open_torque: Opening torque
            - close_torque: Closing torque
            - pressure_drop: Pressure drop value
            - test_result: Test result (PASS/FAIL)
            - status: Status code (1 for PASS, 0 for FAIL)
    """
    try:
        # Extract values from dictionary with defaults
        result_psr = test_data.get('result_psr')
        start_pressure = test_data.get('start_pressure')
        end_pressure = test_data.get('end_pressure')
        pressure_drop = test_data.get('pressure_drop')
        actual_time = test_data.get('actual_time')
        clamping_psr = test_data.get('clamping_psr')
        open_torque = test_data.get('open_torque')
        close_torque = test_data.get('close_torque')
        start_time = test_data.get('start_time')
        end_time = test_data.get('end_time')
        test_result = test_data.get('test_result')
        status = test_data.get('status')
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                if station_num == 1:
                    # Update temp_pressure_analysis - includes STATUS field
                    cursor.execute("""
                        UPDATE temp_pressure_analysis
                        SET
                            ACTUAL_PRESSURE = %s,
                            START_PRESSURE  = %s,
                            RESULT_PRESSURE = %s,
                            LEAK_PRESSURE = %s,
                            ACTUAL_TIME=%s,
                            CLAMPING_PRESSURE = %s,
                            ACTUAL_OPEN_TORQUE =%s,
                            ACTUAL_CLOSE_TORQUE = %s,
                            `START` = %s,
                            `END` = %s,
                            VALVE_STATUS = %s,
                            STATUS = %s,
                            DATE_TIME = NOW()
                        WHERE TEST_ID = %s
                        AND VALVE_SER_NO = %s
                        AND CYCLE_COMPLETE = 'No'
                    """, [
                        result_psr,
                        start_pressure,
                        end_pressure,
                        pressure_drop,
                        actual_time,
                        clamping_psr,
                        open_torque,
                        close_torque,
                        start_time,
                        end_time,
                        test_result,
                        status,
                        test_id,
                        valve_serial_no
                    ])

                    # Update pressure_analysis
                    cursor.execute("""
                        UPDATE pressure_analysis
                        SET 
                            ACTUAL_PRESSURE = %s,
                            START_PRESSURE  = %s,
                            RESULT_PRESSURE = %s,
                            LEAK_PRESSURE = %s,
                            ACTUAL_TIME=%s,
                            CLAMPING_PRESSURE = %s,
                            ACTUAL_OPEN_TORQUE =%s,
                            ACTUAL_CLOSE_TORQUE = %s,
                            `START` = %s,
                            `END` = %s,
                            VALVE_STATUS = %s ,
                            DATE_TIME = NOW()
                        WHERE TEST_ID = %s
                        AND VALVE_SER_NO = %s
                        AND CYCLE_COMPLETE = 'No'
                    """, [
                        result_psr,
                        start_pressure,
                        end_pressure,
                        pressure_drop,
                        actual_time,
                        clamping_psr,
                        open_torque,
                        close_torque,
                        start_time,
                        end_time,
                        test_result,
                        test_id,
                        valve_serial_no
                    ])

                elif station_num == 2:
                    # Update temp_pressure_analysis - includes STATUS field
                    cursor.execute("""
                        UPDATE temp_pressure_analysis
                        SET 
                            ACTUAL_PRESSURE = %s,
                            START_PRESSURE = %s,
                            RESULT_PRESSURE= %s,
                            LEAK_PRESSURE = %s,
                            ACTUAL_TIME=%s,
                            CLAMPING_PRESSURE = %s,
                            ACTUAL_OPEN_TORQUE =%s,
                            ACTUAL_CLOSE_TORQUE = %s,
                            `START` = %s,
                            `END` = %s,
                            VALVE_STATUS = %s,
                            STATUS = %s,
                            DATE_TIME = NOW()
                        WHERE TEST_ID = %s
                        AND VALVE_SER_NO = %s
                        AND CYCLE_COMPLETE = 'No'
                    """, [
                        result_psr,
                        start_pressure,
                        end_pressure,
                        pressure_drop,
                        actual_time,
                        clamping_psr,
                        open_torque,
                        close_torque,
                        start_time,
                        end_time,
                        test_result,
                        status,
                        test_id,
                        valve_serial_no
                    ])
                    
                    # Update pressure_analysis
                    cursor.execute("""
                        UPDATE pressure_analysis
                        SET 
                            ACTUAL_PRESSURE = %s,
                            START_PRESSURE  = %s,
                            RESULT_PRESSURE = %s,
                            LEAK_PRESSURE = %s,
                            ACTUAL_TIME=%s,
                            CLAMPING_PRESSURE = %s,
                            ACTUAL_OPEN_TORQUE =%s,
                            ACTUAL_CLOSE_TORQUE = %s,
                            `START` = %s,
                            `END` = %s,
                            VALVE_STATUS = %s,
                            DATE_TIME = NOW()
                        WHERE TEST_ID = %s
                        AND VALVE_SER_NO = %s
                        AND CYCLE_COMPLETE = 'No'
                    """, [
                        result_psr,
                        start_pressure,
                        end_pressure,
                        pressure_drop,
                        actual_time,
                        clamping_psr,
                        open_torque,
                        close_torque,
                        start_time,
                        end_time,
                        test_result,
                        test_id,
                        valve_serial_no
                    ])
                    
        print(f"[SERVICE] Successfully updated tested values for Station {station_num}, Test ID: {test_id}")
        return True
        
    except Exception as e:
        print(f"[SERVICE] Error updating tested values: {e}")
        import traceback
        traceback.print_exc()
        raise
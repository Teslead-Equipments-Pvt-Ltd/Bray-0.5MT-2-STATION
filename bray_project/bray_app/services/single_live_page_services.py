# from django.db import connection, transaction, IntegrityError
# from django.http import JsonResponse



# def save_test_pressure_station1(id, name, valve_serial_no, station_data1, final_data_1, cursor):

#     parameters = final_data_1.get("PARAMETERS", {})

   
#     #Check existing latest record for this valve (based on serial number only)
    
#     default_count = 1   
#     count = 0
#     cursor.execute("""
#         select Count_No from serial_tbl where Serial_No = %s
#         """, [valve_serial_no])
#     row = cursor.fetchone()
#     if row is None:
#         serial_count = None  
#     else:
#         serial_count = row[0]
    
#     if serial_count:
#         cursor.execute("""
#             SELECT CYCLE_COMPLETE
#             FROM pressure_analysis
#             WHERE VALVE_SER_NO = %s AND COUNT_ID = %s
#             ORDER BY COUNT_ID DESC
#             LIMIT 1
#         """, [valve_serial_no, serial_count])
#         row = cursor.fetchone()
#         if row:
#             cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
#                        """,[valve_serial_no, id])
#             row2 = cursor.fetchone()
#             if row2:
#                     insert_new = False
                    
#             else:
#                 count = serial_count + 1
#                 insert_new = True
#     else:
#         # Continue same cycle → UPDATE
#         cursor.execute(""" select CYCLE_COMPLETE from temp_pressure_analysis where VALVE_SER_NO = %s AND TEST_ID = %s
#                        """,[valve_serial_no, id])
#         row2 = cursor.fetchone()
#         if row2:
#             insert_new = False
#         else:
#             count = default_count
#             insert_new = True
        
#     #Common columns
    
#     columns = [
#         "TEST_ID",
#         "TEST_NAME",
#         "VALVE_SER_NO",
#         "COUNT_ID",
#         "CYCLE_COMPLETE",
#         "SET_PRESSURE",
#         "PRESSURE_UNIT",
#         "SET_TIME",
#         "SET_TIME_UNIT",
#         "STANDARD_NAME",
#         "VALVESIZE_NAME",
#         "VALVETYPE_NAME",
#         "VALVECLASS_NAME",
#         "SHELLMATERIAL_NAME"
#     ]

#     values = ["%s"] * len(columns)

#     data = [
#         id,
#         name,
#         valve_serial_no,
#         count,
#         "No",   # default cycle status
#         station_data1.get("TESTING_PRESSURE"),
#         station_data1.get("TESTING_PSR_UNIT"),
#         station_data1.get("TESTING_DUR"),
#         station_data1.get("TESTING_DUR_UNIT"),
#         final_data_1.get("STANDARD_NAME"),
#         final_data_1.get("SIZE_NAME"),
#         final_data_1.get("TYPE_NAME"),
#         final_data_1.get("CLASS_NAME"),
#         final_data_1.get("SHELL_MATERIAL_NAME")
#     ]

#     # Dynamic parameter columns
    
#     index = 1
#     for param_name, param_value in parameters.items():
#         if index > 23:
#             break

#         columns.extend([f"COL{index}_NAME", f"COL{index}_VALUE"])
#         values.extend(["%s", "%s"])
#         data.extend([param_name, param_value])
#         index += 1

#     # INSERT or UPDATE logic
   

#     tables = ["temp_pressure_analysis", "pressure_analysis"]

#     with transaction.atomic():
#         for table in tables:

#             if insert_new:
#                 sql = f"""
#                     INSERT INTO {table}
#                     ({', '.join(columns)})
#                     VALUES ({', '.join(values)})
#                 """
#                 cursor.execute(sql, data)

#             else:
#                 # fields to update (exclude keys)
#                 update_fields = [f"{col} = %s" for col in columns[5:]]

#                 sql = f"""
#                     UPDATE {table}
#                     SET {', '.join(update_fields)}
#                     WHERE VALVE_SER_NO = %s AND COUNT_ID = %s
#                 """

#                 #build correct update data
#                 update_data = (
#                     data[5:] +        # values for SET columns
#                     [valve_serial_no, count]  # WHERE values
#                 )

#                 cursor.execute(sql, update_data)


# def save_test_pressure_station2(id, name, valve_serial_no, station_data2, final_data_2, cursor):

#     parameters = final_data_2.get("PARAMETERS", {})

   
#     #Check existing latest record for this valve
    
#     cursor.execute("""
#         SELECT COUNT_ID, CYCLE_COMPLETE
#         FROM pressure_analysis
#         WHERE TEST_ID = %s AND VALVE_SER_NO = %s
#         ORDER BY COUNT_ID DESC
#         LIMIT 1
#     """, [id, valve_serial_no])

#     row = cursor.fetchone()

#     if row:
#         last_count, cycle_complete = row

#         if cycle_complete == "Yes":
#             # New cycle → NEW ROW
#             count_2 = last_count + 1
#             insert_new_2 = True
#         else:
#             # Continue same cycle → UPDATE
#             count_2 = last_count
#             insert_new_2 = False
#     else:
#         # First time valve
#         count_2 = 1
#         insert_new_2 = True

   
#     #Common columns
    
#     columns = [
#         "TEST_ID",
#         "TEST_NAME",
#         "VALVE_SER_NO",
#         "COUNT_ID",
#         "CYCLE_COMPLETE",
#         "SET_PRESSURE",
#         "PRESSURE_UNIT",
#         "SET_TIME",
#         "SET_TIME_UNIT",
#         "STANDARD_NAME",
#         "VALVESIZE_NAME",
#         "VALVETYPE_NAME",
#         "VALVECLASS_NAME",
#         "SHELLMATERIAL_NAME"
#     ]

#     values = ["%s"] * len(columns)

#     data = [
#         id,
#         name,
#         valve_serial_no,
#         count_2,
#         "No",   # default cycle status
#         station_data2.get("TESTING_PRESSURE"),
#         station_data2.get("TESTING_PSR_UNIT"),
#         station_data2.get("TESTING_DUR"),
#         station_data2.get("TESTING_DUR_UNIT"),
#         final_data_2.get("STANDARD_NAME"),
#         final_data_2.get("SIZE_NAME"),
#         final_data_2.get("TYPE_NAME"),
#         final_data_2.get("CLASS_NAME"),
#         final_data_2.get("SHELL_MATERIAL_NAME")
#     ]

#     # Dynamic parameter columns
    
#     index = 1
#     for param_name, param_value in parameters.items():
#         if index > 23:
#             break

#         columns.extend([f"COL{index}_NAME", f"COL{index}_VALUE"])
#         values.extend(["%s", "%s"])
#         data.extend([param_name, param_value])
#         index += 1

#     # INSERT or UPDATE logic
   

#     tables_2 = ["temp_pressure_analysis", "pressure_analysis"]

#     with transaction.atomic():
#         for table in tables_2:

#             if insert_new_2:
#                 sql = f"""
#                     INSERT INTO {table}
#                     ({', '.join(columns)})
#                     VALUES ({', '.join(values)})
#                 """
#                 cursor.execute(sql, data)

#             else:
#                 # fields to update (exclude keys)
#                 update_fields = [f"{col} = %s" for col in columns[5:]]

#                 sql = f"""
#                     UPDATE {table}
#                     SET {', '.join(update_fields)}
#                     WHERE TEST_ID = %s AND VALVE_SER_NO = %s AND COUNT_ID = %s
#                 """

#                 #build correct update data
#                 update_data = (
#                     data[5:] +        # values for SET columns
#                     [id, valve_serial_no, count_2]  # WHERE values
#                 )

#                 cursor.execute(sql, update_data)


# def clear_station_1():
#     with transaction.atomic():
#         with connection.cursor() as cursor:
#             cursor.execute("TRUNCATE TABLE current_status_station1")

# def clear_station_2():
#     with transaction.atomic():
#         with connection.cursor() as cursor:
#             cursor.execute("TRUNCATE TABLE current_status_station2")

# def clear_s1_livedata():
#     print("calling clear_s1_livedata view function")
#     with connection.cursor() as cursor:
#         cursor.execute("Truncate table current_status_station1")
#         cursor.execute("select VALVE_SER_NO, TEST_ID, COUNT_ID from temp_pressure_analysis")
#         results = cursor.fetchall()
        
#         # Check if there's data in temp_pressure_analysis before processing
#         if results:
#             # Loop through all rows and delete each matching record
#             for row in results:
#                 serial_no = row[0]  # VALVE_SER_NO
#                 test_id = row[1]    # TEST_ID
#                 count_id = row[2]   # COUNT_ID
                               
#                 cursor.execute(
#                     "DELETE FROM pressure_analysis WHERE VALVE_SER_NO = %s AND TEST_ID = %s AND COUNT_ID = %s", 
#                     (serial_no, test_id, count_id)
#                 )
        
#         cursor.execute("truncate temp_pressure_analysis")

# def clear_s2_livedata():
#     with connection.cursor() as cursor:
#         cursor.execute("Truncate table current_status_station2")
#         cursor.execute("select VALVE_SER_NO, TEST_ID, COUNT_ID from temp_pressure_analysis")
#         results = cursor.fetchall()
        
#         # Check if there's data in temp_pressure_analysis before processing
#         if results:
#             # Loop through all rows and delete each matching record
#             for row in results:
#                 serial_no = row[0]  # VALVE_SER_NO
#                 test_id = row[1]    # TEST_ID
#                 count_id = row[2]   # COUNT_ID
                               
#                 cursor.execute(
#                     "DELETE FROM pressure_analysis WHERE VALVE_SER_NO = %s AND TEST_ID = %s AND COUNT_ID = %s", 
#                     (serial_no, test_id, count_id)
#                 )
        
#         cursor.execute("truncate temp_pressure_analysis")
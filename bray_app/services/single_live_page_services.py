from django.db import connection, transaction, IntegrityError
from django.http import JsonResponse




# def save_test_values_s1(id, name, valve_serial_no, station_data1):

#     try:
#         #temp_pressure_analysis
#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE temp_pressure_analysis
#                 SET
#                     PRESSURE_UNIT = %s,
#                     SET_PRESSURE = %s,
#                     SET_TIME_UNIT = %s,
#                     SET_TIME = %s
#                     WHERE TEST_ID = %s
#                     AND TEST_NAME = %s
#                     AND VALVE_SER_NO = %s
#                 """

#             insert_query = """
#                 INSERT INTO temp_pressure_analysis (
#                     VALVE_SER_NO,
#                     TEST_ID,
#                     TEST_NAME,
#                     PRESSURE_UNIT,
#                     SET_PRESSURE,
#                     SET_TIME_UNIT,
#                     SET_TIME
#                 )
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """

#             for item in station_data1:
#                 cursor.execute(update_query, (
#                     item["TESTING_PSR_UNIT"],
#                     item["TESTING_PRESSURE"],
#                     item["TESTING_DUR_UNIT"],
#                     item["TESTING_DUR"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item["TESTING_PSR_UNIT"],
#                         item["TESTING_PRESSURE"],
#                         item["TESTING_DUR_UNIT"],
#                         item["TESTING_DUR"]
#                     ))

#         #pressure analysis table
#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE pressure_analysis
#                     SET
#                     PRESSURE_UNIT = %s,
#                     SET_PRESSURE = %s,
#                     SET_TIME_UNIT = %s,
#                     SET_TIME = %s
#                     WHERE TEST_ID = %s
#                     AND TEST_NAME = %s
#                     AND VALVE_SER_NO = %s
#                     """

#             insert_query = """
#                 INSERT INTO pressure_analysis (
#                     VALVE_SER_NO,
#                     TEST_ID,
#                     TEST_NAME,
#                     PRESSURE_UNIT,
#                     SET_PRESSURE,
#                     SET_TIME_UNIT,
#                     SET_TIME
#                 )
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """

#             for item2 in station_data1:
#                 cursor.execute(update_query, (
#                     item2["TESTING_PSR_UNIT"],
#                     item2["TESTING_PRESSURE"],
#                     item2["TESTING_DUR_UNIT"],
#                     item2["TESTING_DUR"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item2["TESTING_PSR_UNIT"],
#                         item2["TESTING_PRESSURE"],
#                         item2["TESTING_DUR_UNIT"],
#                         item2["TESTING_DUR"]
#                     ))

#         return JsonResponse({
#             "status":"success",
#             "message":"data saved succefully in both table" 
            
#         })

#     except Exception as e:
#         print("ERROR:", e)
#         return JsonResponse({"status": "error", "message": str(e)}, status=500)



     

# def save_test_pressure_s1(id, name, valve_serial_no, master_station1_data):
        
#         #update temp pressure analysis
#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE temp_pressure_analysis
#                 SET
#                 STANDARD_NAME = %s,
#                 VALVESIZE_NAME =%s,
#                 VALVETYPE_NAME =%s,
#                 VALVECLASS_NAME = %s,
#                 SHELLMATERIAL_NAME =%s 
#                 WHERE TEST_ID = %s
#                 AND TEST_NAME = %s
#                 AND VALVE_SER_NO = %s
#                     """
            
#             insert_query = """
#                 INSERT INTO temp_pressure_analysis (
#                 STANDARD_NAME, 
#                 VALVESIZE_NAME, 
#                 VALVETYPE_NAME, 
#                 VALVECLASS_NAME, 
#                 SHELLMATERIAL_NAME
#                 )
#                 VALUES (%s, %s, %s, %s, %s)
#             """

#             for item in master_station1_data:
#                 cursor.execute(update_query, (
#                     item["STANDARD_NAME"],
#                     item["VALVESIZE_NAME"],
#                     item["VALVETYPE_NAME"],
#                     item["VALVECLASS_NAME"],
#                     item["SHELLMATERIAL_NAME"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item["STANDARD_NAME"],
#                         item["VALVESIZE_NAME"],
#                         item["VALVETYPE_NAME"],
#                         item["TVALVECLASS_NAME"],
#                         item["SHELLMATERIAL_NAME"],
#                     ))

#         #update prssure analysis
#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE pressure_analysis
#                 SET
#                 STANDARD_NAME = %s,
#                 VALVESIZE_NAME =%s,
#                 VALVETYPE_NAME =%s,
#                 VALVECLASS_NAME = %s,
#                 SHELLMATERIAL_NAME =%s 
#                 WHERE TEST_ID = %s
#                 AND TEST_NAME = %s
#                 AND VALVE_SER_NO = %s
#                 """
            
#             insert_query = """
#                 INSERT INTO pressure_analysis (
#                 STANDARD_NAME, 
#                 VALVESIZE_NAME, 
#                 VALVETYPE_NAME, 
#                 VALVECLASS_NAME, 
#                 SHELLMATERIAL_NAME
#                 )
#                 VALUES (%s, %s, %s, %s, %s)
#             """

#             for item in master_station1_data:
#                 cursor.execute(update_query, (
#                     item["STANDARD_NAME"],
#                     item["VALVESIZE_NAME"],
#                     item["VALVETYPE_NAME"],
#                     item["VALVECLASS_NAME"],
#                     item["SHELLMATERIAL_NAME"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item["STANDARD_NAME"],
#                         item["VALVESIZE_NAME"],
#                         item["VALVETYPE_NAME"],
#                         item["VALVECLASS_NAME"],
#                         item["SHELLMATERIAL_NAME"],
#                     ))

def save_test_pressure_station1(id, name, valve_serial_no, station_data1, final_data_1, cursor):

    parameters = final_data_1.get("PARAMETERS", {})

   
    #Check existing latest record for this valve
    
    cursor.execute("""
        SELECT COUNT_ID, CYCLE_COMPLETE
        FROM pressure_analysis
        WHERE TEST_ID = %s AND VALVE_SER_NO = %s
        ORDER BY COUNT_ID DESC
        LIMIT 1
    """, [id, valve_serial_no])

    row = cursor.fetchone()

    if row:
        last_count, cycle_complete = row

        if cycle_complete == "Yes":
            # New cycle → NEW ROW
            count = last_count + 1
            insert_new = True
        else:
            # Continue same cycle → UPDATE
            count = last_count
            insert_new = False
    else:
        # First time valve
        count = 1
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
                cursor.execute(sql, data)

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

                cursor.execute(sql, update_data)


def save_test_pressure_station2(id, name, valve_serial_no, station_data2, final_data_2, cursor):

    parameters = final_data_2.get("PARAMETERS", {})

   
    #Check existing latest record for this valve
    
    cursor.execute("""
        SELECT COUNT_ID, CYCLE_COMPLETE
        FROM pressure_analysis
        WHERE TEST_ID = %s AND VALVE_SER_NO = %s
        ORDER BY COUNT_ID DESC
        LIMIT 1
    """, [id, valve_serial_no])

    row = cursor.fetchone()

    if row:
        last_count, cycle_complete = row

        if cycle_complete == "Yes":
            # New cycle → NEW ROW
            count_2 = last_count + 1
            insert_new_2 = True
        else:
            # Continue same cycle → UPDATE
            count_2 = last_count
            insert_new_2 = False
    else:
        # First time valve
        count_2 = 1
        insert_new_2 = True

   
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
        count_2,
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
   

    tables_2 = ["temp_pressure_analysis", "pressure_analysis"]

    with transaction.atomic():
        for table in tables_2:

            if insert_new_2:
                sql = f"""
                    INSERT INTO {table}
                    ({', '.join(columns)})
                    VALUES ({', '.join(values)})
                """
                cursor.execute(sql, data)

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
                    [id, valve_serial_no, count_2]  # WHERE values
                )

                cursor.execute(sql, update_data)


# def save_test_pressure_station2(id, name, valve_serial_no, station2_data, final_data_2, cursor):

#     parameters = final_data_2.get("PARAMETERS", {})

#     columns = [
#         "TEST_ID",
#         "TEST_NAME",
#         "VALVE_SER_NO",
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
#         station2_data.get("TESTING_PRESSURE"),
#         station2_data.get("TESTING_PSR_UNIT"),
#         station2_data.get("TESTING_DUR"),
#         station2_data.get("TESTING_DUR_UNIT"),
#         final_data_2.get("STANDARD_NAME"),
#         final_data_2.get("SIZE_NAME"),
#         final_data_2.get("TYPE_NAME"),
#         final_data_2.get("CLASS_NAME"),
#         final_data_2.get("SHELL_MATERIAL_NAME")
#     ]

#     update_fields = []

#     index = 1
#     for param_name, param_value in parameters.items():
#         if index > 23:
#             break

#         columns.append(f"COL{index}_NAME")
#         columns.append(f"COL{index}_VALUE")

#         values.extend(["%s", "%s"])
#         data.extend([param_name, param_value])

#         update_fields.append(f"COL{index}_NAME = VALUES(COL{index}_NAME)")
#         update_fields.append(f"COL{index}_VALUE = VALUES(COL{index}_VALUE)")

#         index += 1

#     # update fixed fields also
#     update_fields.extend([
#         "SET_PRESSURE = VALUES(SET_PRESSURE)",
#         "PRESSURE_UNIT = VALUES(PRESSURE_UNIT)",
#         "SET_TIME = VALUES(SET_TIME)",
#         "SET_TIME_UNIT = VALUES(SET_TIME_UNIT)",
#         "STANDARD_NAME = VALUES(STANDARD_NAME)",
#         "VALVESIZE_NAME = VALUES(VALVESIZE_NAME)",
#         "VALVETYPE_NAME = VALUES(VALVETYPE_NAME)",
#         "VALVECLASS_NAME = VALUES(VALVECLASS_NAME)",
#         "SHELLMATERIAL_NAME = VALUES(SHELLMATERIAL_NAME)"
#     ])

#     # insert_query = f"""
#     #     INSERT INTO temp_pressure_analysis
#     #     ({', '.join(columns)})
#     #     VALUES ({', '.join(values)})
#     #     ON DUPLICATE KEY UPDATE
#     #     {', '.join(update_fields)}
#     # """

#     # cursor.execute(insert_query, data)

     
#     insert_sql = f"""
#         INSERT INTO {{table}}
#         ({', '.join(columns)})
#         VALUES ({', '.join(values)})
#         ON DUPLICATE KEY UPDATE
#         {', '.join(update_fields)}
#     """

#     with transaction.atomic():
#         cursor.execute(insert_sql.format(table="temp_pressure_analysis"), data)
        # cursor.execute(insert_sql.format(table="pressure_analysis"), data)



# def save_test_values_s2(id, name, valve_serial_no, station_data2):

#     try:
#         #temp_pressure_analysis
#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE temp_pressure_analysis
#                 SET
#                     PRESSURE_UNIT = %s,
#                     SET_PRESSURE = %s,
#                     SET_TIME_UNIT = %s,
#                     SET_TIME = %s
#                     WHERE TEST_ID = %s
#                     AND TEST_NAME = %s
#                     AND VALVE_SER_NO = %s
#                 """

#             insert_query = """
#                 INSERT INTO temp_pressure_analysis (
#                     VALVE_SER_NO,
#                     TEST_ID,
#                     TEST_NAME,
#                     PRESSURE_UNIT,
#                     SET_PRESSURE,
#                     SET_TIME_UNIT,
#                     SET_TIME
#                 )
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """

#             for item in station_data2:
#                 cursor.execute(update_query, (
#                     item["TESTING_PSR_UNIT"],
#                     item["TESTING_PRESSURE"],
#                     item["TESTING_DUR_UNIT"],
#                     item["TESTING_DUR"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item["TESTING_PSR_UNIT"],
#                         item["TESTING_PRESSURE"],
#                         item["TESTING_DUR_UNIT"],
#                         item["TESTING_DUR"]
#                     ))

#         #pressure analysis table
#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE pressure_analysis
#                     SET
#                     PRESSURE_UNIT = %s,
#                     SET_PRESSURE = %s,
#                     SET_TIME_UNIT = %s,
#                     SET_TIME = %s
#                     WHERE TEST_ID = %s
#                     AND TEST_NAME = %s
#                     AND VALVE_SER_NO = %s
#                     """

#             insert_query = """
#                 INSERT INTO pressure_analysis (
#                     VALVE_SER_NO,
#                     TEST_ID,
#                     TEST_NAME,
#                     PRESSURE_UNIT,
#                     SET_PRESSURE,
#                     SET_TIME_UNIT,
#                     SET_TIME
#                 )
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """

#             for item2 in station_data2:
#                 cursor.execute(update_query, (
#                     item2["TESTING_PSR_UNIT"],
#                     item2["TESTING_PRESSURE"],
#                     item2["TESTING_DUR_UNIT"],
#                     item2["TESTING_DUR"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item2["TESTING_PSR_UNIT"],
#                         item2["TESTING_PRESSURE"],
#                         item2["TESTING_DUR_UNIT"],
#                         item2["TESTING_DUR"]
#                     ))

#         return JsonResponse({
#             "status":"success",
#             "message":"data saved succefully in both table" 
            
#         })

#     except Exception as e:
#         print("ERROR:", e)
#         return JsonResponse({"status": "error", "message": str(e)}, status=500)



    

# def save_test_pressure_s2(id, name, valve_serial_no, master_station2_data):

#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE temp_pressure_analysis
#                 SET
#                 STANDARD_NAME = %s,
#                 VALVESIZE_NAME =%s,
#                 VALVETYPE_NAME =%s,
#                 VALVECLASS_NAME = %s,
#                 SHELLMATERIAL_NAME =%s 
#                 WHERE TEST_ID = %s
#                 AND TEST_NAME = %s
#                 AND VALVE_SER_NO = %s
#                     """
            
#             insert_query = """
#                 INSERT INTO temp_pressure_analysis (
#                 STANDARD_NAME, 
#                 VALVESIZE_NAME, 
#                 VALVETYPE_NAME, 
#                 VALVECLASS_NAME, 
#                 SHELLMATERIAL_NAME
#                 )
#                 VALUES (%s, %s, %s, %s, %s)
#             """

#             for item in master_station2_data:
#                 cursor.execute(update_query, (
#                     item["STANDARD_NAME"],
#                     item["VALVESIZE_NAME"],
#                     item["VALVETYPE_NAME"],
#                     item["VALVECLASS_NAME"],
#                     item["SHELLMATERIAL_NAME"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item["STANDARD_NAME"],
#                         item["VALVESIZE_NAME"],
#                         item["VALVETYPE_NAME"],
#                         item["TVALVECLASS_NAME"],
#                         item["SHELLMATERIAL_NAME"],
#                     ))

#         with connection.cursor() as cursor:
#             update_query = """
#                 UPDATE pressure_analysis
#                 SET
#                 STANDARD_NAME = %s,
#                 VALVESIZE_NAME =%s,
#                 VALVETYPE_NAME =%s,
#                 VALVECLASS_NAME = %s,
#                 SHELLMATERIAL_NAME =%s 
#                 WHERE TEST_ID = %s
#                 AND TEST_NAME = %s
#                 AND VALVE_SER_NO = %s
#                 """
            
#             insert_query = """
#                 INSERT INTO pressure_analysis (
#                 STANDARD_NAME, 
#                 VALVESIZE_NAME, 
#                 VALVETYPE_NAME, 
#                 VALVECLASS_NAME, 
#                 SHELLMATERIAL_NAME
#                 )
#                 VALUES (%s, %s, %s, %s, %s)
#             """

#             for item in master_station2_data:
#                 cursor.execute(update_query, (
#                     item["STANDARD_NAME"],
#                     item["VALVESIZE_NAME"],
#                     item["VALVETYPE_NAME"],
#                     item["VALVECLASS_NAME"],
#                     item["SHELLMATERIAL_NAME"],
#                     id,
#                     name,
#                     valve_serial_no
#                 ))

#                 # If no row updated → INSERT
#                 if cursor.rowcount == 0:
#                     cursor.execute(insert_query, (
#                         valve_serial_no,
#                         id,
#                         name,
#                         item["STANDARD_NAME"],
#                         item["VALVESIZE_NAME"],
#                         item["VALVETYPE_NAME"],
#                         item["TVALVECLASS_NAME"],
#                         item["SHELLMATERIAL_NAME"],
#                     ))





def clear_station_1():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE current_status_station1")

def clear_station_2():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE current_status_station2")
from django.db import connection, transaction, IntegrityError
from django.http import JsonResponse
import json
from django.shortcuts import redirect
from django.contrib import messages
from bray_app.decorators import permission_required
from django.views.decorators.csrf import csrf_exempt
from bray_app.services.valvesize_service import get_all_valvesize, get_all_valvetype, get_enabled_categories, delete_multiple_valvesize

def valve_size_list(request):

    if request.method != "GET":
        return JsonResponse ({"error":"Invalid method"}, staus=405) 

    valves = get_all_valvesize()

    valve_list=[]
    for valve in valves:
        valve_list.append({
            "ID" : valve[0],
            "SIZE_ID":valve[1],
            "SIZE_NAME":valve[2],
            "SIZE_DESC":valve[3],
            "PART_NO":valve[4] if len(valve) > 4 else "",
            "PART_NAME":valve[5] if len(valve) > 5 else ""
        })
    
    return JsonResponse({
        "valve_list" : valve_list
    })
    

def get_all_valve_type(request):

    if request.method != "GET":
        return JsonResponse ({"error":"Invalid method"}, status=405)
    
    valve_type = get_all_valvetype()

    valve_type_list = []
    for type in valve_type:
        valve_type_list.append({
            "TYPE_ID" : type[0],
            "TYPE_NAME": type[1]
        })

    return JsonResponse({
        "valve_type_list" : valve_type_list
    })
    

def get_enabled_category(request):

    if request.method != "GET":
        return JsonResponse ({"error":"Invalid method"}, status = 405)
    
    enabled_categories = get_enabled_categories()

    enabled_categories_list = []
    for Ecategories in enabled_categories:

        enabled_categories_list.append({
            "CATEGORY_NAME": Ecategories[0],
            "DURATION_COLUMN_NAME":Ecategories[1]
        })

    return JsonResponse({
        "enabled_categories_list" : enabled_categories_list
    })


 
def edit_valve_list(request, size_id):

    edit_valve = None
    if request.method != "GET":
        return JsonResponse ({"error":"Invalid method"}, status = 405)
    
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ID, SIZE_ID, SIZE_NAME, SIZE_DESC, PART_NO, PART_NAME
                FROM valvesize WHERE SIZE_ID =%s
            """, [size_id])
            row = cursor.fetchone()
            if row:
                edit_valve = dict(zip(["id", "size_id", "name", "description", "part_no", "part_name"], row))


        enabled_categories = get_enabled_categories()
        duration_data = []
        degree_data = []

        # Fetch duration data
        with connection.cursor() as cursor:
            col_names = ", ".join(col_name for _, col_name in enabled_categories)
            cursor.execute(f"""
                SELECT ID, STANDARD_ID, {col_names}
                FROM master_duration_data
                WHERE SIZE_ID=%s
                ORDER BY SIZE_ID
            """, [edit_valve['size_id']])
            
            for d in cursor.fetchall():
                entry = {"id": d[0], "standard_id": d[1]}
                for i, (_, col_name) in enumerate(enabled_categories):
                    entry[col_name] = d[i + 2]
                    
                duration_data.append(entry)

        # Fetch degree data
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ID, TYPE_ID, OPEN_DEGREE, CLOSE_DEGREE, LOADING_AND_UNLOADING_DEGREE
                FROM master_degree_data
                WHERE SIZE_ID=%s 
            """, [edit_valve['size_id']])
            for row in cursor.fetchall():
                degree_data.append({
                    "id":row[0],
                    "valve_type_id": row[1],
                    "open_degree": row[2],
                    "close_degree": row[3],
                    "loading_unloading_degree": row[4],
                    "extra": True
                })

        return JsonResponse({
            "success": True,
            "message": "Valve size retrieved successfully",
            "edit_valve": edit_valve,
            "duration_data": duration_data,
            "degree_data":degree_data,
        })
    
    else:
        return JsonResponse({"error": "Not found"}, status=404)

@csrf_exempt
def add_valve_size(request):
  
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
    
    try:
        data = json.loads(request.body)
    
        size_id = data.get("size_id", "").strip()
        name = data.get("valve_name", "").strip()
        desc = data.get("valve_des", "").strip()
        part_no = data.get("part_no", "").strip()
        part_name = data.get("part_name", "").strip()
        category_values = data.get("duration_rows", [])
        degree_values = data.get("degree_rows", [])

        if not size_id:
            return JsonResponse({   
                "status": "error",
                "message": "Valve size ID cannot be empty."
            }, status=400)

        if not name:
            return JsonResponse({   
                "status": "error",
                "message": "Valve name cannot be empty."
            }, status=400)

        if not part_no:
            return JsonResponse({   
                "status": "error",
                "message": "Part No cannot be empty."
            }, status=400)

        if not part_name:
            return JsonResponse({   
                "status": "error",
                "message": "Part Name cannot be empty."
            }, status=400)

        with connection.cursor() as cursor:
            # Check for duplicate size_id
            cursor.execute("""
                SELECT 1 FROM valvesize
                WHERE SIZE_ID = %s
            """,[size_id])

            duplicate_id = cursor.fetchone()

            if duplicate_id:
                return JsonResponse({
                    "status":"error",
                    "message":"Valve size ID already exists. Please use a different ID."
                }, status=409)

            # Check for duplicate name
            cursor.execute("""
                SELECT 1 FROM valvesize
                WHERE SIZE_NAME = %s
            """,[name])

            duplicate = cursor.fetchone()

            if duplicate:
                return JsonResponse({
                    "status":"error",
                    "message":"Valve size name already exists. Duplicate names are not allowed"
                }, status=409)
            
            # Insert with user-provided size_id and new fields
            cursor.execute("""
                INSERT INTO valvesize (SIZE_ID, SIZE_NAME, SIZE_DESC, PART_NO, PART_NAME)
                VALUES (%s, %s, %s, %s, %s)
            """, [size_id, name, desc, part_no, part_name])

            new_valve_id = size_id

            # --- MASTER DURATION DATA ---
            for row in category_values:
                standard_id = row.get("standard_id")

                # Remove standard_id from column dict
                duration_cols = {k: v for k, v in row.items() if k != "standard_id"}

                col_names = ", ".join(duration_cols.keys())
                placeholders = ", ".join(["%s"] * len(duration_cols))
                values = list(duration_cols.values())

                cursor.execute(
                    f"""
                    INSERT INTO master_duration_data 
                    (SIZE_ID, STANDARD_ID, {col_names})
                    VALUES (%s, %s, {placeholders})
                    """,
                    [new_valve_id, standard_id] + values
                )

            # --- MASTER DEGREE DATA --
            for row in degree_values:
                cursor.execute("""
                    INSERT INTO master_degree_data
                    (SIZE_ID, TYPE_ID, OPEN_DEGREE, CLOSE_DEGREE, LOADING_AND_UNLOADING_DEGREE)
                    VALUES (%s, %s, %s, %s, %s)
                """, [
                    new_valve_id,
                    row.get("type_id"),
                    row.get("open_degree"),
                    row.get("close_degree"),
                    row.get("loading_unloading_degree"),
                ])
        return JsonResponse({"status": "success", "message": "Valve size saved!"})

    except IntegrityError as e:
        return JsonResponse({"status": "error", "message": f"Database error: {str(e)}"}, status=500)
    
    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
        

def delete_valve_size(request, size_id):
    print("Received size_id:", size_id)   

    
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                cursor.execute("SELECT SIZE_ID FROM valvesize WHERE SIZE_ID=%s", [size_id])
                row = cursor.fetchone()

                if row is None:
                    print("No record found for ID:", size_id)
                    return JsonResponse({"error": "Valve size not found."}, status=404)

                    
                size_code = row[0]

                # Delete related duration data
                cursor.execute("DELETE FROM master_duration_data WHERE SIZE_ID=%s", [size_code])
                
                # Delete related degree data
                cursor.execute("DELETE FROM master_degree_data WHERE SIZE_ID=%s", [size_code])
                
                # Delete the valve size itself
                cursor.execute("DELETE FROM valvesize WHERE SIZE_ID=%s", [size_id])

        return JsonResponse({"success": True, "message": "Valve Size deleted successfully!"})
    
    except Exception as e:
        print("Error deleting valve:", e)
        return JsonResponse({"success": False, "message": str(e)}, status=500)



def update_valve_size(request, size_id):
    print("Received size_id:", size_id)   


    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
    
    try:
        data = json.loads(request.body)
    
        new_size_id = data.get("size_id", "").strip()
        name = data.get("valve_name", "").strip()
        desc = data.get("valve_des", "").strip()
        part_no = data.get("part_no", "").strip()
        part_name = data.get("part_name", "").strip()
        duration_values = data.get("duration_rows", [])
        degree_values = data.get("degree_rows", [])

        if not new_size_id:
            return JsonResponse({   
                "status": "error",
                "message": "Valve size ID cannot be empty."
            }, status=400)

        if not part_no:
            return JsonResponse({   
                "status": "error",
                "message": "Part No cannot be empty."
            }, status=400)

        if not part_name:
            return JsonResponse({   
                "status": "error",
                "message": "Part Name cannot be empty."
            }, status=400)

        with connection.cursor() as cursor:
            # Check for duplicate size_id (excluding current record)
            cursor.execute("""
                SELECT ID FROM valvesize
                WHERE SIZE_ID = %s AND SIZE_ID != %s
            """,[new_size_id, size_id])

            duplicate_id = cursor.fetchone()

            if duplicate_id:
                return JsonResponse({
                    "status":"error",
                    "message":"Valve size ID already exists. Please use a different ID."
                }, status=409)

            # Check for duplicate name (excluding current record)
            cursor.execute("""
                SELECT ID FROM valvesize
                WHERE SIZE_NAME = %s AND SIZE_ID !=%s
            """,[name, size_id])

            duplicate = cursor.fetchone()

        if duplicate:
            return JsonResponse({
                "status":"error",
                "message":"Valve size name already exists. Duplicate names are not allowed"
            }, status=409)

        with transaction.atomic():
            with connection.cursor() as cursor:
                # Update valve size with new size_id and new fields if changed
                cursor.execute("""
                    UPDATE valvesize 
                    SET 
                    SIZE_ID=%s,
                    SIZE_NAME=%s, 
                    SIZE_DESC=%s,
                    PART_NO=%s,
                    PART_NAME=%s
                    WHERE SIZE_ID = %s
                """, [new_size_id, name, desc, part_no, part_name, size_id])

                # If size_id changed, update related tables
                if new_size_id != size_id:
                    cursor.execute("""
                        UPDATE master_duration_data 
                        SET SIZE_ID = %s
                        WHERE SIZE_ID = %s
                    """, [new_size_id, size_id])

                    cursor.execute("""
                        UPDATE master_degree_data 
                        SET SIZE_ID = %s
                        WHERE SIZE_ID = %s
                    """, [new_size_id, size_id])
            
                frontend_ids = [row.get("ogi_id") for row in duration_values if row.get("ogi_id")]

                if frontend_ids:
                    cursor.execute("""
                            DELETE FROM master_duration_data 
                            WHERE SIZE_ID = %s AND ID NOT IN (%s)
                            """ % ("%s", ",".join(["%s"] * len(frontend_ids))), [new_size_id] + frontend_ids)
                else:
                    cursor.execute("DELETE FROM master_duration_data WHERE SIZE_ID = %s", [new_size_id])

            
                # --- MASTER DURATION DATA ---#
                for row in duration_values:

                    standard_og_id = row.get("ogi_id")
                    standard_id = row.get("standard_id")
                
                    duration_cols = {k: v for k, v in row.items() if k not in ("ogi_id", "standard_id")}

                    if standard_og_id :
                        set_clause = ", ".join([f"{k} = %s" for k in duration_cols.keys()])

                        values = list(duration_cols.values())
                        
                        cursor.execute(f"""
                            UPDATE master_duration_data 
                                SET STANDARD_ID = %s, {set_clause} 
                                WHERE ID = %s AND SIZE_ID = %s
                                """,
                                [standard_id] + values  + [standard_og_id , new_size_id]
                        )
                    else:
                        col_names = ", ".join(duration_cols.keys())
                        placeholders = ", ".join(["%s"] * len(duration_cols))
                        values = list(duration_cols.values())

                        cursor.execute(
                            f"""
                            INSERT INTO master_duration_data 
                            (SIZE_ID, STANDARD_ID, {col_names})
                            VALUES (%s, %s, {placeholders})
                            """,
                            [new_size_id, standard_id] + values
                        )

                # --- MASTER DEGREE DATA --

                frontend_type_ids = [row.get("ogi_type_id") for row in degree_values if row.get("ogi_type_id")]
                print("forntendy_ids", frontend_type_ids)

                if frontend_type_ids:
                    placeholders = ",".join(["%s"] * len(frontend_type_ids))
                    print(placeholders)
                    cursor.execute(
                        f"""
                        DELETE FROM master_degree_data
                        WHERE SIZE_ID = %s AND ID NOT IN ({placeholders})
                        """,
                        [new_size_id] + frontend_type_ids
                    )


                for row in degree_values:
                    type_id= row.get("type_id")
                    valvetype_og_id = row.get("ogi_type_id")
                    
                    open_d = row.get("open_degree")
                    close_d = row.get("close_degree")
                    load_unload_d = row.get("loading_unloading_degree")

                    print("received degree_values", row)

                    if valvetype_og_id:
                        cursor.execute("""
                            UPDATE master_degree_data
                            SET
                            TYPE_ID = %s,
                            OPEN_DEGREE = %s, 
                            CLOSE_DEGREE= %s, 
                            LOADING_AND_UNLOADING_DEGREE = %s
                            WHERE ID = %s AND  SIZE_ID = %s
                        """, [
                            type_id,
                            open_d,
                            close_d,
                            load_unload_d,
                            valvetype_og_id,
                            new_size_id
                        ])
                        print("updated")

                    else:
                        cursor.execute("""
                            INSERT INTO master_degree_data
                            (SIZE_ID, TYPE_ID, OPEN_DEGREE, CLOSE_DEGREE, LOADING_AND_UNLOADING_DEGREE)
                            VALUES (%s, %s, %s, %s, %s)
                    """, [
                            new_size_id,
                            type_id,
                            open_d,
                            close_d,
                            load_unload_d,
                           
                    ])
                        
                    print("inserted")

            return JsonResponse({"status": "success", "message": "Valve Size Updated!"})       
    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)




def to_int_or_none(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


@csrf_exempt
def bulk_delete_valvesize_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])

        if not ids:
            return JsonResponse({"error": "No IDs provided"})

        deleted_count = delete_multiple_valvesize(ids)

        return JsonResponse({"success": True, "deleted_count": deleted_count, "message": "Valve Sizes deleted successfully"})
    except Exception as e:
        return JsonResponse({"success": False,"error": str(e)}, status=500)




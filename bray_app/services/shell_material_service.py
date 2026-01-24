from django.db import connection, transaction
# from django.db.utils import IntegrityError


def get_all_materials():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME, SHELL_MATERIAL_DESC
            FROM shell_material ORDER BY SHELL_MATERIAL_ID
        """)
        return cursor.fetchall()


def get_next_shell_material_id():
    """Get the next available SHELL_MATERIAL_ID"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(SHELL_MATERIAL_ID), 0) + 1 FROM shell_material")
        return cursor.fetchone()[0]


def get_all_classes():
    with connection.cursor() as cursor:
        cursor.execute("SELECT CLASS_ID, CLASS_NAME FROM valveclass ORDER BY CLASS_ID")
        return cursor.fetchall()


def get_enabled_categories():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME, PRESSURE_COLUMN_NAME
            FROM category WHERE STATUS='ENABLE'
            ORDER BY ID
        """)
        return cursor.fetchall()


def get_material_detail(material_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME, SHELL_MATERIAL_DESC
            FROM shell_material WHERE ID=%s
        """, [material_id])
        row = cursor.fetchone()
        return row


def get_pressure_data(shell_id, categories):
    with connection.cursor() as cursor:
        col_names = ", ".join(col for _, col in categories)

        cursor.execute(f"""
            SELECT ID, VALVECLASS_ID, {col_names}
            FROM master_pressure_data
            WHERE SHELLMATERIAL_ID=%s
            ORDER BY ID
        """, [shell_id])

        return cursor.fetchall()


def save_shell_material(data, categories):
    """
    Insert/Update shell_material + master_pressure_data
    data = {
       "material_id": 12 or None,
       "shell_id": 4,
       "name": "...",
       "desc": "...",
       "rows": [ {class_id:1, 'CAT_A':12, 'CAT_B':30}, {...} ]
    }
    """
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                # INSERT or UPDATE shell_material
                if data["material_id"]:
                    cursor.execute("""
                        UPDATE shell_material
                        SET SHELL_MATERIAL_NAME=%s, SHELL_MATERIAL_DESC=%s
                        WHERE ID=%s
                    """, [data["name"], data["desc"], data["material_id"]])
                else:
                    cursor.execute("""
                        INSERT INTO shell_material (SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME, SHELL_MATERIAL_DESC)
                        VALUES (%s, %s, %s)
                    """, [data["shell_id"], data["name"], data["desc"]])

                # DELETE removed pressure rows (only if rows exist)
                if data["rows"]:
                    class_ids = [r["class_id"] for r in data["rows"]]
                    cursor.execute("""
                        DELETE FROM master_pressure_data
                        WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID NOT IN %s
                    """, [data["shell_id"], tuple(class_ids)])
                else:
                    # If no rows, delete all pressure data for this shell material
                    cursor.execute("""
                        DELETE FROM master_pressure_data
                        WHERE SHELLMATERIAL_ID=%s
                    """, [data["shell_id"]])

                # UPSERT pressure rows
                for row in data["rows"]:
                    cursor.execute("""
                        SELECT COUNT(*) FROM master_pressure_data
                        WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID=%s
                    """, [data["shell_id"], row["class_id"]])

                    exists = cursor.fetchone()[0]

                    if exists:
                        set_clause = ", ".join([f"{col}=%s" for _, col in categories])
                        values = [row[col] for _, col in categories]
                        cursor.execute(f"""
                            UPDATE master_pressure_data
                            SET {set_clause}
                            WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID=%s
                        """, values + [data["shell_id"], row["class_id"]])
                    else:
                        col_names = ", ".join(col for _, col in categories)
                        placeholders = ", ".join(["%s"] * len(categories))
                        values = [row[col] for _, col in categories]
                        cursor.execute(f"""
                            INSERT INTO master_pressure_data
                            (SHELLMATERIAL_ID, VALVECLASS_ID, {col_names})
                            VALUES (%s, %s, {placeholders})
                        """, [data["shell_id"], row["class_id"]] + values)

        return True
    except Exception as e:
        error_msg = str(e).lower()
        # Check for unique constraint violations
        if 'unique' in error_msg or 'duplicate' in error_msg:
            if 'shell_material_name' in error_msg or data["name"].lower() in error_msg:
                raise ValueError(f"Shell Material Name '{data['name']}' already exists. Please use a different name.")
        # Re-raise the original exception if it's not a unique constraint error
        raise


def delete_shell_material(shell_id):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM master_pressure_data WHERE SHELLMATERIAL_ID=%s", [shell_id])

def delete_multiple_shell_materials(shell_ids):
    if not shell_ids:
        return 0

    placeholders = ",".join(["%s"] * len(shell_ids))
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            # Delete related pressure data first
            cursor.execute(f"DELETE FROM master_pressure_data WHERE SHELLMATERIAL_ID IN ({placeholders})", shell_ids)
            # Delete materials
            cursor.execute(f"DELETE FROM shell_material WHERE SHELL_MATERIAL_ID IN ({placeholders})", shell_ids)
            return cursor.rowcount

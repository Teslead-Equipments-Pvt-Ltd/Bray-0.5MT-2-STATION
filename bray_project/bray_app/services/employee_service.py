from django.db import connection, transaction
from django.contrib.auth.hashers import make_password


def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_all_employees():
    """Get all non-superuser employees."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, employee_type, code, name, password, email, mobile, image, status
            FROM employee
            WHERE superuser = 0
            ORDER BY id
        """)
        rows = cursor.fetchall()
        return [
            {
                'id': r[0],
                'employee_type': r[1],
                'code': r[2],
                'name': r[3],
                'password': r[4],
                'email': r[5],
                'mobile': r[6],
                'image': r[7],
                'status': r[8]
            }
            for r in rows
        ]


def get_employee_by_id(employee_id):
    """Get a single employee by ID."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, employee_type, code, name, password, email, mobile, image, status
            FROM employee
            WHERE id = %s
        """, [employee_id])
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'employee_type': row[1],
                'code': row[2],
                'name': row[3],
                'password': row[4],
                'email': row[5],
                'mobile': row[6],
                'image': row[7],
                'status': row[8]
            }
        return None


def get_employee_permissions(employee_ids):
    """Get permissions for a list of employee IDs."""
    if not employee_ids:
        return {}
    
    permissions_map = {emp_id: [] for emp_id in employee_ids}
    placeholders = ','.join(['%s'] * len(employee_ids))
    
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT employee_id, menu_item_id
            FROM newapp_usermenupermission
            WHERE employee_id IN ({placeholders})
        """, employee_ids)
        for emp_id, menu_id in cursor.fetchall():
            if emp_id in permissions_map:
                permissions_map[emp_id].append(int(menu_id))
    
    return permissions_map


def get_existing_employee_codes():
    """Get all existing employee codes for validation."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT code FROM employee WHERE superuser = 0")
        return [r[0] for r in cursor.fetchall()]


def get_menu_items_by_section():
    """Get menu items grouped by section in the desired order.
    MASTER section contains: Standard, Valve Size, Valve Class, Valve Type, Shell Material, Gauge Details, Alarm
    Then separate sections for Report, etc.
    Excludes Employee, Category, Instrument Type, Test Type, Accounting User Accounting, Access Control, ABRS, Settings."""
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, section
            FROM newapp_menuitem
            WHERE name NOT IN ('Employee', 'Category', 'Instrument Type', 'Test Type', 'Test type', 'Accounting User Accounting', 'Access Control')
            AND UPPER(TRIM(section)) NOT IN ('ABRS', 'SETTINGS', '')
            AND section IS NOT NULL
            ORDER BY section, name
        """)
        menu_items = dictfetchall(cursor)
    
    # Define the MASTER section items in the desired order (including Alarm)
    master_items = [
        'Standard',
        'Valve Size', 
        'Valve Class',
        'Valve Type',
        'Shell Material',
        'Gauge Details',
        'Alarm'
    ]
    
    # Create ordered dictionary with sections
    menu_items_by_section = {}
    
    # First, create MASTER section with items in specific order
    master_section = []
    remaining_items = []
    
    for item in menu_items:
        if item['name'] in master_items:
            master_section.append(item)
        else:
            remaining_items.append(item)
    
    # Sort master section items according to desired order
    master_section_ordered = []
    for master_name in master_items:
        for item in master_section:
            if item['name'] == master_name:
                master_section_ordered.append(item)
                break
    
    # Add MASTER section if it has items
    if master_section_ordered:
        menu_items_by_section['MASTER'] = master_section_ordered
    
    # Group remaining items by their original sections
    temp_sections = {}
    
    for item in remaining_items:
        section = item['section']
        # Normalize section name to uppercase for consistency (and trim whitespace)
        section_normalized = section.strip().upper() if section else 'OTHER'
        # For all sections, add all items (ABRS and Settings already excluded in query)
        if section_normalized not in temp_sections:
            temp_sections[section_normalized] = []
        temp_sections[section_normalized].append(item)
    
    # Define the desired order for remaining sections (after MASTER)
    remaining_order = [
        'REPORT'
    ]
    
    # Add remaining sections in desired order
    for section_name in remaining_order:
        if section_name in temp_sections:
            menu_items_by_section[section_name] = temp_sections[section_name]
    
    # Add any other sections that weren't in the desired order
    for section_name in sorted(temp_sections.keys()):
        if section_name not in remaining_order and section_name not in menu_items_by_section:
            menu_items_by_section[section_name] = temp_sections[section_name]
    
    return menu_items_by_section


def check_duplicate_code(code, exclude_id=None):
    """Check if employee code already exists."""
    with connection.cursor() as cursor:
        if exclude_id:
            cursor.execute("SELECT COUNT(*) FROM employee WHERE code=%s AND id != %s", [code, exclude_id])
        else:
            cursor.execute("SELECT COUNT(*) FROM employee WHERE code=%s", [code])
        return cursor.fetchone()[0] > 0


@transaction.atomic
def insert_employee(employee_type, code, name, password, email, mobile, image, status=None):
    """Insert a new employee and return the new ID."""
    # Hash the password before storing
    hashed_password = make_password(password) if password else None
    # Default status to 'active' if not provided
    employee_status = status if status else 'active'
    
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO employee (employee_type, code, name, password, email, mobile, image, superuser, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s)
        """, [employee_type, code, name, hashed_password, email, mobile, image, employee_status])
        
        cursor.execute("SELECT id FROM employee WHERE code=%s", [code])
        row = cursor.fetchone()
        return row[0] if row else None


@transaction.atomic
def update_employee(employee_id, employee_type, code, name, password, email, mobile, status=None, image=None):
    """Update an existing employee. Password is only updated if provided."""
    # Default status to 'active' if not provided
    employee_status = status if status else 'active'
    
    with connection.cursor() as cursor:
        if password:
            # Hash the new password
            hashed_password = make_password(password)
            if image:
                cursor.execute("""
                    UPDATE employee
                    SET employee_type=%s, code=%s, name=%s, password=%s, email=%s, mobile=%s, image=%s, status=%s
                    WHERE id=%s
                """, [employee_type, code, name, hashed_password, email, mobile, image, employee_status, employee_id])
            else:
                cursor.execute("""
                    UPDATE employee
                    SET employee_type=%s, code=%s, name=%s, password=%s, email=%s, mobile=%s, status=%s
                    WHERE id=%s
                """, [employee_type, code, name, hashed_password, email, mobile, employee_status, employee_id])
        else:
            # Don't update password if not provided
            if image:
                cursor.execute("""
                    UPDATE employee
                    SET employee_type=%s, code=%s, name=%s, email=%s, mobile=%s, image=%s, status=%s
                    WHERE id=%s
                """, [employee_type, code, name, email, mobile, image, employee_status, employee_id])
            else:
                cursor.execute("""
                    UPDATE employee
                    SET employee_type=%s, code=%s, name=%s, email=%s, mobile=%s, status=%s
                    WHERE id=%s
                """, [employee_type, code, name, email, mobile, employee_status, employee_id])


@transaction.atomic
def delete_employee(employee_id):
    """Delete an employee and their permissions."""
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM newapp_usermenupermission WHERE employee_id=%s", [employee_id])
        cursor.execute("DELETE FROM employee WHERE id=%s", [employee_id])


@transaction.atomic
def delete_multiple_employees(ids):
    """Delete multiple employees."""
    if not ids:
        return 0
    
    placeholders = ','.join(['%s'] * len(ids))
    
    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM newapp_usermenupermission WHERE employee_id IN ({placeholders})", ids)
        cursor.execute(f"DELETE FROM employee WHERE id IN ({placeholders})", ids)
        return cursor.rowcount


@transaction.atomic
def update_employee_permissions(employee_id, menu_item_ids):
    """Update permissions for an employee."""
    with connection.cursor() as cursor:
        # Delete all existing permissions for this employee
        cursor.execute("DELETE FROM newapp_usermenupermission WHERE employee_id=%s", [employee_id])
        
        # Insert new permissions
        for item_id in menu_item_ids:
            if item_id:
                cursor.execute("""
                    INSERT INTO newapp_usermenupermission (employee_id, menu_item_id)
                    VALUES (%s, %s)
                """, [employee_id, int(item_id)])

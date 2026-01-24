from datetime import datetime
from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
from dateutil.parser import parse as parse_date
from pymodbus.client import ModbusTcpClient
from .decorators import login_required, permission_required, superuser_required
from django.contrib.auth.hashers import make_password, check_password as check_pwd
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction, IntegrityError
from django.utils import timezone
from django.contrib import messages

actual_pressure = None
TestleadSmartsyncx = None

# Check HMI connection

def hmi(): 
    global TestleadSmartsyncx      
    try:
        # TestleadSmartsyncx = ModbusTcpClient('192.168.1.20')
        TestleadSmartsyncx = ModbusTcpClient('127.0.0.1')
        TestleadSmartsyncx.connect()
    except Exception as e:
        print(f"Error connecting Modbus: {e}")
hmi()


def login(request):
    request.session.flush()  
    request.session.referer = request.META.get('HTTP_REFERER', '/')
    request.session['is_authenticated'] = False
   
    return render(request, 'new_login.html')
   


def new_username(request):
    """Check if username exists and fetch role using raw SQL + cursor"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()

        if not username:
            return JsonResponse({'status': 'error', 'message': 'Username is required'})

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, superuser FROM employee WHERE name = %s",
                [username]
            )
            row = cursor.fetchone()

        if not row:
            return JsonResponse({'status': 'error', 'message': 'Username not found'})

        name, superuser = row

        return JsonResponse({
            'status': 'success',
            'username': name,
            'superuser': superuser
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



def new_pwd(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            return JsonResponse({'status': 'error', 'message': 'Missing username or password'})

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT name, password, superuser FROM employee WHERE name = %s",
                    [username]
                )
                row = cursor.fetchone()

            if not row:
                return JsonResponse({'status': 'error', 'message': 'User not found'})

            db_name, db_password, db_superuser = row
  

            # if password == db_password:
            if check_pwd(password, db_password):
                # Manually set session
                request.session['username'] = db_name
                request.session['superuser'] = db_superuser
                request.session['is_authenticated'] = True  # Mark as fully authenticated

                return JsonResponse({
                    'status': 'success',
                    'username': db_name,
                    'superuser': 'yes' if db_superuser else 'no',
                    'message': 'Login successful!'
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Incorrect password'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        employee_username = request.session.get('username')
        if not employee_username:
            messages.error(request, "Session expired. Please log in again.")
            return redirect('login')

        try:
            # Fetch employee record using raw SQL
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT password FROM employee WHERE name = %s",
                    [employee_username]
                )
                row = cursor.fetchone()

            if not row:
                messages.error(request, "User not found.")
                return redirect('login')

            db_password = row[0]

            # Check old password using Django's check_password for hashed passwords
            if not check_pwd(old_password, db_password):
                messages.error(request, "Old password is incorrect.")
                return redirect('change_password')

            # Check new/confirm match
            if new_password != confirm_password:
                messages.error(request, "New password and Confirm password do not match.")
                return redirect('change_password')

            # Hash the new password before storing
            hashed_password = make_password(new_password)
            
            # Update password in DB
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE employee SET password = %s WHERE name = %s",
                    [hashed_password, employee_username]
                )

            messages.success(request, "Password updated successfully.")
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f"Error updating password: {str(e)}")
            return redirect('change_password')

    # GET request - render change password page
    return render(request, 'dashboard.html')

@login_required
def check_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            old_password = data.get('old_password')
            employee_username = request.session.get('username')

            if not employee_username:
                return JsonResponse({'valid': False, 'error': 'Session expired'})

            with connection.cursor() as cursor:
                cursor.execute("SELECT password FROM employee WHERE name = %s", [employee_username])
                row = cursor.fetchone()

            if not row:
                return JsonResponse({'valid': False, 'error': 'User not found'})

            db_password = row[0]
            # Use Django's check_password to verify hashed password
            if check_pwd(old_password, db_password):
                return JsonResponse({'valid': True})
            else:
                return JsonResponse({'valid': False, 'error': 'Old password is incorrect'})
        except Exception as e:
            return JsonResponse({'valid': False, 'error': f'Server error: {str(e)}'})
    return JsonResponse({'error': 'Invalid method'}, status=405)



def dashboard(request):
    return render(request,'dashboard_new.html')


def custom_logout(request):
    username = request.session.get('username')
    password = request.session.get('password')

    if username and password:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE employee SET last_logout = %s WHERE name = %s AND password = %s",
                [current_time, username, password]
            )

    request.session.flush()
    request.session['logout_message'] = "Logout successful"

    return redirect('login')



# --- List standards ---


@permission_required("Standard")
def standard_list(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, STANDARD_ID, STANDARD_NAME, STANDARD_DESC, CREATED_DATE, UPDATED_DATE
            FROM standard
            ORDER BY ID
        """)
        standards = cursor.fetchall()

    # Extract only names for frontend duplicate check
    existing_names = [row[2] for row in standards]  # STANDARD_NAME

    return render(request, 'standard_list.html', {
        'standards': standards,
        'existing_names': existing_names,
    })


@permission_required("Standard")
def add_standard(request):
    if request.method == 'POST':
        STANDARD_NAME = request.POST.get("name")
        STANDARD_DESC = request.POST.get("description")

        if STANDARD_NAME:
            with connection.cursor() as cursor:
                # calculate next STANDARD_ID
                cursor.execute("SELECT COALESCE(MAX(STANDARD_ID),0)+1 FROM standard")
                next_standard_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO standard (STANDARD_ID, STANDARD_NAME, STANDARD_DESC) VALUES (%s, %s, %s)",
                    [next_standard_id, STANDARD_NAME, STANDARD_DESC]
                )

            messages.success(request, 'Standard added successfully!')
        else:
            messages.error(request, 'Standard name is required.')

    return redirect('standard_list')


@permission_required("Standard")
def edit_standard(request, pk):
    if request.method == 'POST':
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, 'Standard name cannot be empty.')
            return redirect('standard_list')

        with connection.cursor() as cursor:
            # Check for duplicates excluding current ID
            cursor.execute("SELECT 1 FROM standard WHERE STANDARD_NAME=%s AND ID != %s", [name, pk])
            if cursor.fetchone():
                messages.error(request, 'Another standard with this name already exists.')
                return redirect('standard_list')

            # Update record using ID
            cursor.execute("""
                UPDATE standard
                SET STANDARD_NAME=%s, STANDARD_DESC=%s
                WHERE ID=%s
            """, [name, description, pk])

        messages.success(request, 'Standard updated successfully!')

    return redirect('standard_list')

@permission_required("Standard")
def delete_standard(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM standard WHERE ID=%s", [pk])
        messages.success(request, 'Standard deleted successfully!')

    return redirect('standard_list')


# Valve Size List

def to_int_or_none(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

def valve_size_list(request):
    # --- Fetch valves ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, SIZE_ID, SIZE_NAME, SIZE_DESC
            FROM valvesize
            ORDER BY SIZE_ID
        """)
        valves = cursor.fetchall()

    # --- Fetch standards ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT STANDARD_ID, STANDARD_NAME
            FROM standard
            ORDER BY STANDARD_ID
        """)
        standards = cursor.fetchall()

    # --- Fetch valve types ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TYPE_ID, TYPE_NAME
            FROM valve_type
            ORDER BY TYPE_ID
        """)
        valve_types = cursor.fetchall()

    # --- Fetch enabled categories ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME, DURATION_COLUMN_NAME
            FROM category
            WHERE STATUS='ENABLE'
            ORDER BY CATEGORY_ID
        """)
        categories = cursor.fetchall()

    edit_valve = None
    duration_data = []
    degree_data = []

    # --- POST: Save/Update Valve Size ---
    if request.method == "POST":
        valve_id = request.POST.get("valve_id")
        name = request.POST.get("name", "").strip()
        desc = request.POST.get("description", "").strip()

        # --- Standard + Duration data ---
        standards_selected = request.POST.getlist("standard[]")
        category_values = {
            col_name: request.POST.getlist(col_name + "[]")
            for _, col_name in categories
        }

        # --- Valve-type degree data ---
        extra_valve_types = request.POST.getlist("valve_type[]")
        extra_open_vals = request.POST.getlist("open_degree[]")
        extra_close_vals = request.POST.getlist("close_degree[]")
        extra_loading_vals = request.POST.getlist("loading_unloading_degree[]")

        # --- Determine SIZE_ID ---
        with connection.cursor() as cursor:
            if valve_id and valve_id.isdigit():
                # Existing valve → fetch SIZE_ID
                cursor.execute("SELECT SIZE_ID FROM valvesize WHERE ID=%s", [valve_id])
                result = cursor.fetchone()
                size_id = str(result[0]) if result else None
            else:
                # New valve → generate new SIZE_ID
                cursor.execute("SELECT COALESCE(MAX(SIZE_ID),0)+1 FROM valvesize")
                size_id = str(cursor.fetchone()[0])

        if not size_id:
            messages.error(request, "Unable to determine Valve Code.")
            return redirect("valve_size_list")

        # --- Duplicate check ---
        with connection.cursor() as cursor:
            if valve_id and valve_id.isdigit():
                cursor.execute("SELECT COUNT(*) FROM valvesize WHERE SIZE_ID=%s AND ID<>%s", [size_id, valve_id])
            else:
                cursor.execute("SELECT COUNT(*) FROM valvesize WHERE SIZE_ID=%s", [size_id])
            if cursor.fetchone()[0] > 0:
                messages.error(request, f"Valve Code '{size_id}' already exists.")
                return redirect("valve_size_list")

        # --- Build duration data ---
        rows_data_duration = []
        for i, std_id in enumerate(standards_selected):
            if not std_id:
                continue
            row = {'standard_id': std_id}
            for _, col_name in categories:
                vals = category_values.get(col_name, [])
                row[col_name] = to_int_or_none(vals[i]) if i < len(vals) else None
            rows_data_duration.append(row)

        # --- Build degree data ---
        rows_data_degree = []
        for i, vtype_id in enumerate(extra_valve_types):
            if not vtype_id:
                continue
            rows_data_degree.append({
                "type_id": vtype_id,
                "open_degree": to_int_or_none(extra_open_vals[i]) if i < len(extra_open_vals) else None,
                "close_degree": to_int_or_none(extra_close_vals[i]) if i < len(extra_close_vals) else None,
                "loading_unloading_degree": to_int_or_none(extra_loading_vals[i]) if i < len(extra_loading_vals) else None,
            })

        # --- Database insert/update ---
        with transaction.atomic():
            with connection.cursor() as cursor:
                try:
                    # --- Insert/Update valvesize ---
                    if valve_id and valve_id.isdigit():
                        cursor.execute("""
                            UPDATE valvesize SET SIZE_NAME=%s, SIZE_DESC=%s WHERE ID=%s
                        """, [name, desc, valve_id])
                        new_valve_id = valve_id
                    else:
                        cursor.execute("""
                            INSERT INTO valvesize (SIZE_ID, SIZE_NAME, SIZE_DESC)
                            VALUES (%s, %s, %s)
                        """, [int(size_id), name, desc])
                        new_valve_id = cursor.lastrowid

                    # --- MASTER DURATION DATA ---
                    cursor.execute("DELETE FROM master_duration_data WHERE SIZE_ID=%s", [size_id])
                    for row in rows_data_duration:
                        col_names = ", ".join(col_name for _, col_name in categories)
                        placeholders = ", ".join(["%s"] * len(categories))
                        cursor.execute(f"""
                            INSERT INTO master_duration_data (SIZE_ID, STANDARD_ID, {col_names})
                            VALUES (%s, %s, {placeholders})
                        """, [
                            int(size_id),
                            row['standard_id'],
                            *[row[col] for _, col in categories]
                        ])

                    # --- MASTER DEGREE DATA ---
                    cursor.execute("DELETE FROM master_degree_data WHERE SIZE_ID=%s", [size_id])
                    for row in rows_data_degree:
                        cursor.execute("""
                            INSERT INTO master_degree_data
                            (SIZE_ID, TYPE_ID, OPEN_DEGREE, CLOSE_DEGREE, LOADING_AND_UNLOADING_DEGREE)
                            VALUES (%s, %s, %s, %s, %s)
                        """, [
                            int(size_id),
                            row['type_id'],
                            row['open_degree'],
                            row['close_degree'],
                            row['loading_unloading_degree'],
                        ])
                except IntegrityError as e:
                    messages.error(request, f"Database error: {str(e)}")
                    return redirect("valve_size_list")

        messages.success(request, f"Valve Size {size_id} saved successfully!")
        return redirect("valve_size_list")

    # --- GET: Edit Valve Size ---
    if request.method == "GET" and "edit" in request.GET:
        valve_id = request.GET.get("edit")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ID, SIZE_ID, SIZE_NAME, SIZE_DESC
                FROM valvesize WHERE ID=%s
            """, [valve_id])
            row = cursor.fetchone()
            if row:
                edit_valve = dict(zip(["id", "code", "name", "description"], row))

        # Fetch duration data
        with connection.cursor() as cursor:
            col_names = ", ".join(col_name for _, col_name in categories)
            cursor.execute(f"""
                SELECT ID, STANDARD_ID, {col_names}
                FROM master_duration_data
                WHERE SIZE_ID=%s
                ORDER BY ID
            """, [edit_valve['code']])
            for d in cursor.fetchall():
                entry = {"id": d[0], "standard_id": d[1]}
                for i, (_, col_name) in enumerate(categories):
                    entry[col_name] = d[i + 2]
                duration_data.append(entry)

        # Fetch degree data
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TYPE_ID, OPEN_DEGREE, CLOSE_DEGREE, LOADING_AND_UNLOADING_DEGREE
                FROM master_degree_data
                WHERE SIZE_ID=%s
            """, [edit_valve['code']])
            for row in cursor.fetchall():
                degree_data.append({
                    "valve_type_id": row[0],
                    "open_degree": row[1],
                    "close_degree": row[2],
                    "loading_unloading_degree": row[3],
                    "extra": True
                })

    # --- Existing codes/names ---
    with connection.cursor() as cursor:
        cursor.execute("SELECT SIZE_ID, SIZE_NAME FROM valvesize")
        existing_rows = cursor.fetchall()
        existing_codes = [str(r[0]) for r in existing_rows]
        existing_names = [r[1] for r in existing_rows if r[1]]

    all_categories_disabled = len(categories) == 0

    return render(request, 'valve_size.html', {
        'valves': valves,
        'edit_valve': edit_valve,
        'duration_data': duration_data,
        'degree_data': degree_data,
        'standards': standards,
        'categories': categories,
        'existing_codes': existing_codes,
        'existing_names': existing_names,
        'all_categories_disabled': all_categories_disabled,
        'valve_types': valve_types
    })


@permission_required("Valve Size")
def valve_size_delete(request, pk):
    if request.method == 'POST':
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Fetch SIZE_ID (code) for this valve
                cursor.execute("SELECT SIZE_ID FROM valvesize WHERE ID=%s", [pk])
                row = cursor.fetchone()
                if not row:
                    messages.error(request, "Valve Size not found.")
                    return redirect('valve_size_list')

                size_code = row[0]

                # Delete related duration data
                cursor.execute("DELETE FROM master_duration_data WHERE SIZE_ID=%s", [size_code])
                
                # Delete related degree data
                cursor.execute("DELETE FROM master_degree_data WHERE SIZE_ID=%s", [size_code])
                
                # Delete the valve size itself
                cursor.execute("DELETE FROM valvesize WHERE ID=%s", [pk])

        messages.success(request, 'Valve Size deleted successfully!')
    return redirect('valve_size_list')


# Valve Class List

@permission_required("Valve Class")
def valve_class_list(request):
    # --- Fetch all valve classes ---
    with connection.cursor() as cursor:
        cursor.execute("SELECT ID, CLASS_ID, CLASS_NAME, CLASS_DESC FROM valveclass ORDER BY ID")
        rows = cursor.fetchall()
        valves = [{'id': r[0], 'code': r[1], 'name': r[2], 'description': r[3]} for r in rows]

        # Existing codes and names for validation
        cursor.execute("SELECT CLASS_ID FROM valveclass")
        existing_codes_raw = [str(r[0]) for r in cursor.fetchall()]
        cursor.execute("SELECT CLASS_NAME FROM valveclass")
        existing_names_raw = [r[0] for r in cursor.fetchall()]

    existing_codes = mark_safe(json.dumps(existing_codes_raw))
    existing_names = mark_safe(json.dumps(existing_names_raw))

   
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        valve_id = request.POST.get('valve_id')
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()

    
        if not name:
            messages.error(request, "Valve Class Name is required.")
            return redirect('valve_class')

    
        if form_type == 'add' or not code.isdigit():
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(CLASS_ID), 0) + 1 FROM valveclass")
                next_id = cursor.fetchone()[0]
            code = str(next_id)

    
        if form_type == 'add':
            with connection.cursor() as cursor:
                # Duplicate check
                cursor.execute(
                    "SELECT COUNT(*) FROM valveclass WHERE CLASS_ID=%s OR LOWER(CLASS_NAME)=LOWER(%s)",
                    [code, name]
                )
                if cursor.fetchone()[0] > 0:
                    messages.error(request, f"Valve Class with ID '{code}' or Name '{name}' already exists.")
                    return redirect('valve_class')

                # Insert new record
                cursor.execute(
                    "INSERT INTO valveclass (CLASS_ID, CLASS_NAME, CLASS_DESC) VALUES (%s, %s, %s)",
                    [int(code), name, description]
                )

            messages.success(request, "Valve Class added successfully!")
            return redirect('valve_class')

 
        elif form_type == 'edit' and valve_id:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Duplicate name check excluding current record
                    cursor.execute(
                        "SELECT COUNT(*) FROM valveclass WHERE LOWER(CLASS_NAME)=LOWER(%s) AND ID<>%s",
                        [name, valve_id]
                    )
                    if cursor.fetchone()[0] > 0:
                        messages.error(request, "Valve Class name already exists.")
                        return redirect('valve_class')

                    # Optional: prevent changing CLASS_ID on edit to avoid inserting new ID
                    cursor.execute(
                        "UPDATE valveclass SET CLASS_NAME=%s, CLASS_DESC=%s WHERE ID=%s",
                        [name, description, valve_id]
                    )

            messages.success(request, "Valve Class updated successfully!")
            return redirect('valve_class')

 
    return render(request, 'valve_class.html', {
        'valves': valves,
        'existing_codes': existing_codes,
        'existing_names': existing_names,
    })

@permission_required("Valve Class")
def valve_class_delete(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM valveclass WHERE ID=%s", [pk])
    messages.success(request, 'Valve Class deleted successfully!')
    return redirect('valve_class')


# Valve Type List

@permission_required("Valve Type")
def valve_type_list(request):
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

        # Existing codes & names
        cursor.execute("SELECT TYPE_ID FROM valve_type")
        existing_codes_raw = [str(r[0]) for r in cursor.fetchall()]
        cursor.execute("SELECT TYPE_NAME FROM valve_type")
        existing_names_raw = [r[0] for r in cursor.fetchall()]

    existing_codes = mark_safe(json.dumps(existing_codes_raw))
    existing_names = mark_safe(json.dumps(existing_names_raw))

    # ---------------- POST ----------------
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        selected_test_types = request.POST.getlist('test_types')

        # --- Common validation ---
        if not name:
            messages.error(request, "Valve Type Name cannot be empty.")
            return redirect('valve_type')

        if not selected_test_types:
            messages.error(request, "Please select at least one Test Type before saving.")
            return redirect('valve_type')

        # ---------- ADD OPERATION ----------
        if form_type == 'add':
            with connection.cursor() as cursor:
                # ✅ Generate the next numeric TYPE_ID safely
                cursor.execute("SELECT COALESCE(MAX(TYPE_ID), 0) + 1 FROM valve_type")
                result = cursor.fetchone()
                next_code = int(result[0]) if result and result[0] is not None else 1

                # ✅ Prevent duplicates
                cursor.execute("SELECT COUNT(*) FROM valve_type WHERE TYPE_NAME=%s", [name])
                if cursor.fetchone()[0] > 0:
                    messages.error(request, f"Valve Type '{name}' already exists.")
                    return redirect('valve_type')

                # ✅ Insert valve type
                cursor.execute("""
                    INSERT INTO valve_type (TYPE_ID, TYPE_NAME, TYPE_DESC)
                    VALUES (%s, %s, %s)
                """, [next_code, name, description])

                # ✅ Insert associated test types
                for test_type_id in selected_test_types:
                    cursor.execute("""
                        INSERT INTO valvetype_testtype (TYPE_ID, TEST_ID)
                        VALUES (%s, %s)
                    """, [next_code, test_type_id])

            messages.success(request, f"Valve Type '{name}' added successfully with Code {next_code}!")
            return redirect('valve_type')

        # ---------- EDIT OPERATION ----------
        elif form_type == 'edit':
            valve_id = request.POST.get('valve_id')
            code = request.POST.get('code', '').strip()

            with connection.cursor() as cursor:
                # Fetch TYPE_ID from ID (to avoid empty code)
                if not code:
                    cursor.execute("SELECT TYPE_ID FROM valve_type WHERE ID=%s", [valve_id])
                    fetched = cursor.fetchone()
                    if fetched and fetched[0]:
                        code = int(fetched[0])
                    else:
                        messages.error(request, "Invalid Valve Type code.")
                        return redirect('valve_type')

                # Check for duplicate name
                cursor.execute("SELECT COUNT(*) FROM valve_type WHERE TYPE_NAME=%s AND ID!=%s", [name, valve_id])
                if cursor.fetchone()[0] > 0:
                    messages.error(request, f"Valve Type '{name}' already exists.")
                    return redirect('valve_type')

                # Update valve_type table
                cursor.execute("""
                    UPDATE valve_type
                    SET TYPE_NAME=%s, TYPE_DESC=%s
                    WHERE ID=%s
                """, [name, description, valve_id])

                # Refresh test type links
                cursor.execute("DELETE FROM valvetype_testtype WHERE TYPE_ID=%s", [code])
                for test_type_id in selected_test_types:
                    cursor.execute("""
                        INSERT INTO valvetype_testtype (TYPE_ID, TEST_ID)
                        VALUES (%s, %s)
                    """, [code, test_type_id])

            messages.success(request, f"Valve Type '{name}' updated successfully!")
            return redirect('valve_type')

    # ---------------- DISPLAY ----------------
    valve_test_types = {}
    with connection.cursor() as cursor:
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

    return render(request, 'valve_type.html', {
        'valve_types': valve_types,
        'test_types': test_types,
        'valve_test_types': valve_test_types,
        'existing_codes': existing_codes,
        'existing_names': existing_names,
    })



@permission_required("Valve Type")
def valve_type_delete(request, valve_type_id):
    """Delete a valve type and its associated test type links."""
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT TYPE_NAME, TYPE_ID FROM valve_type WHERE ID=%s", [valve_type_id])
            result = cursor.fetchone()
            if not result:
                messages.error(request, "Valve Type not found.")
                return redirect('valve_type')

            valve_type_name, type_code = result

            cursor.execute("DELETE FROM valvetype_testtype WHERE TYPE_ID=%s", [type_code])
            cursor.execute("DELETE FROM valve_type WHERE ID=%s", [valve_type_id])

            messages.success(request, f'Valve Type "{valve_type_name}" and its associations deleted successfully!')

    except Exception as e:
        messages.error(request, f'Error deleting valve type: {str(e)}')

    return redirect('valve_type')


# # Shell Material List

def dictfetchall(cursor):
    """Return all rows from cursor as dicts"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def to_float_or_none(value):
    """Convert input to float or None safely."""
    try:
        return float(value) if value not in ("", None) else None
    except ValueError:
        return None

@permission_required("Shell Material")
def shell_material(request):
    # --- Fetch all shell materials ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ID, SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME, SHELL_MATERIAL_DESC
            FROM shell_material
            ORDER BY SHELL_MATERIAL_ID
        """)
        materials = cursor.fetchall()

    # --- Fetch valve classes ---
    with connection.cursor() as cursor:
        cursor.execute("SELECT CLASS_ID, CLASS_NAME FROM valveclass ORDER BY CLASS_ID")
        classes = cursor.fetchall()

    # --- Fetch enabled pressure categories ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME, PRESSURE_COLUMN_NAME
            FROM category
            WHERE STATUS='ENABLE'
            ORDER BY ID
        """)
        categories = cursor.fetchall()

    edit_material = None
    pressure_data = []

    # ============================================================
    # --- POST (Save) ---
    # ============================================================
    if request.method == "POST":
        material_id = request.POST.get("material_id")
        name = request.POST.get("name", "").strip()
        desc = request.POST.get("description", "").strip()
        classes_selected = request.POST.getlist("Class[]")

        if not name:
            messages.error(request, "Shell Material Name is required.")
            return redirect("shell_material")

        # --- Determine SHELL_MATERIAL_ID ---
        with connection.cursor() as cursor:
            if material_id and material_id.isdigit():
                # Editing → keep existing ID
                cursor.execute("SELECT SHELL_MATERIAL_ID FROM shell_material WHERE ID=%s", [material_id])
                result = cursor.fetchone()
                code = str(result[0]) if result else None
            else:
                # New record → generate next ID
                cursor.execute("SELECT COALESCE(MAX(SHELL_MATERIAL_ID), 0) + 1 FROM shell_material")
                next_id = cursor.fetchone()[0]
                code = str(next_id)

        if not code:
            messages.error(request, "Unable to determine Shell Material ID.")
            return redirect("shell_material")

        # --- Duplicate ID validation ---
        with connection.cursor() as cursor:
            if material_id and material_id.isdigit():
                cursor.execute("""
                    SELECT COUNT(*) FROM shell_material
                    WHERE SHELL_MATERIAL_ID=%s AND ID<>%s
                """, [code, material_id])
            else:
                cursor.execute("SELECT COUNT(*) FROM shell_material WHERE SHELL_MATERIAL_ID=%s", [code])
            if cursor.fetchone()[0] > 0:
                messages.error(request, f"Shell Material ID '{code}' already exists.")
                return redirect("shell_material")

        # --- Collect category values ---
        category_values = {col: request.POST.getlist(col + "[]") for _, col in categories}

        rows_data = []
        for i, cls_id in enumerate(classes_selected):
            if not cls_id:
                continue
            row = {"class_id": cls_id}
            for _, col in categories:
                vals = category_values.get(col, [])
                row[col] = to_float_or_none(vals[i]) if i < len(vals) else None
            rows_data.append(row)

        # ============================================================
        # --- Insert / Update Logic ---
        # ============================================================
        with transaction.atomic():
            with connection.cursor() as cursor:
                try:
                    # --- Update or Insert shell_material ---
                    if material_id and material_id.isdigit():
                        # ✅ Update existing record
                        cursor.execute("""
                            UPDATE shell_material
                            SET SHELL_MATERIAL_NAME=%s, SHELL_MATERIAL_DESC=%s
                            WHERE ID=%s
                        """, [name, desc, material_id])
                    else:
                        # 🆕 Insert new record
                        cursor.execute("""
                            INSERT INTO shell_material (SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME, SHELL_MATERIAL_DESC)
                            VALUES (%s, %s, %s)
                        """, [int(code), name, desc])

                    # ======================================================
                    # --- Manage master_pressure_data (Update only) ---
                    # ======================================================
                    cursor.execute("SELECT VALVECLASS_ID FROM master_pressure_data WHERE SHELLMATERIAL_ID=%s", [code])
                    existing_class_ids = [str(r[0]) for r in cursor.fetchall()]
                    new_class_ids = [str(r["class_id"]) for r in rows_data]

                    # Delete removed rows
                    deleted_class_ids = list(set(existing_class_ids) - set(new_class_ids))
                    if deleted_class_ids:
                        cursor.execute(
                            f"DELETE FROM master_pressure_data WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID IN ({','.join(['%s']*len(deleted_class_ids))})",
                            [code, *deleted_class_ids]
                        )

                    # Insert or update each class row
                    for row in rows_data:
                        class_id = row["class_id"]

                        cursor.execute("""
                            SELECT COUNT(*) FROM master_pressure_data
                            WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID=%s
                        """, [code, class_id])
                        exists = cursor.fetchone()[0]

                        if exists:
                            # ✅ Update existing pressure data
                            set_clause = ", ".join([f"{col}=%s" for _, col in categories])
                            cursor.execute(f"""
                                UPDATE master_pressure_data
                                SET {set_clause}
                                WHERE SHELLMATERIAL_ID=%s AND VALVECLASS_ID=%s
                            """, [*[row[col] for _, col in categories], code, class_id])
                        else:
                            # 🆕 Insert new one if not present
                            col_names = ", ".join(col for _, col in categories)
                            placeholders = ", ".join(["%s"] * len(categories))
                            cursor.execute(f"""
                                INSERT INTO master_pressure_data (SHELLMATERIAL_ID, VALVECLASS_ID, {col_names})
                                VALUES (%s, %s, {placeholders})
                            """, [code, class_id, *[row[col] for _, col in categories]])

                except IntegrityError as e:
                    messages.error(request, f"Database error: {str(e)}")
                    return redirect("shell_material")

        messages.success(request, f"Shell Material {code} saved successfully!")
        return redirect("shell_material")

    # ============================================================
    # --- GET (Edit) ---
    # ============================================================
    if request.method == "GET" and "edit" in request.GET:
        material_id = request.GET.get("edit")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ID, SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME, SHELL_MATERIAL_DESC
                FROM shell_material
                WHERE ID=%s
            """, [material_id])
            row = cursor.fetchone()
            if row:
                edit_material = dict(zip(["id", "code", "name", "description"], row))

        # --- Fetch pressure data ---
        if edit_material:
            with connection.cursor() as cursor:
                col_names = ", ".join(col for _, col in categories)
                cursor.execute(f"""
                    SELECT ID, VALVECLASS_ID, {col_names}
                    FROM master_pressure_data
                    WHERE SHELLMATERIAL_ID=%s
                    ORDER BY ID
                """, [edit_material["code"]])
                pressure_data = []
                for d in cursor.fetchall():
                    entry = {"id": d[0], "class_id": d[1]}
                    for i, (_, col) in enumerate(categories):
                        entry[col] = d[i + 2]
                    pressure_data.append(entry)

    # ============================================================
    # --- Common Data for Template ---
    # ============================================================
    with connection.cursor() as cursor:
        cursor.execute("SELECT SHELL_MATERIAL_ID, SHELL_MATERIAL_NAME FROM shell_material")
        existing_rows = cursor.fetchall()
        existing_codes = [str(r[0]) for r in existing_rows]
        existing_names = [r[1] for r in existing_rows if r[1]]

    all_categories_disabled = len(categories) == 0

    return render(request, "shell_material.html", {
        "materials": materials,
        "edit_material": edit_material,
        "pressure_data": pressure_data,
        "classes": classes,
        "categories": categories,
        "existing_codes": existing_codes,
        "existing_names": existing_names,
        "all_categories_disabled": all_categories_disabled,
    })


@permission_required("Shell Material")
def shell_material_delete(request, pk):
    if request.method == "POST":
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Check if record exists
                cursor.execute("SELECT id FROM shell_material WHERE SHELL_MATERIAL_ID=%s", [pk])
                if not cursor.fetchone():
                    messages.error(request, "Shell Material not found.")
                    return redirect("shell_material")
                
                # Delete record
                cursor.execute("DELETE FROM shell_material WHERE SHELL_MATERIAL_ID=%s", [pk])

                cursor.execute("DELETE FROM master_pressure_data WHERE SHELLMATERIAL_ID=%s", [pk])

        messages.success(request, "Shell Material deleted successfully!")
    else:
        messages.error(request, "Invalid request method.")

    return redirect("shell_material")




def employee(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, employee_type, code, name, password, email, mobile, image
            FROM employee
            WHERE superuser = 0
            ORDER BY id
        """)
        rows = cursor.fetchall()
        employees = [
            {
                'id': r[0],
                'employee_type': r[1],
                'code': r[2],
                'name': r[3],
                'password': r[4],
                'email': r[5],
                'mobile': r[6],
                'image': r[7]
            }
            for r in rows
        ]
        employee_ids = [emp['id'] for emp in employees]

        permissions_map = {emp_id: [] for emp_id in employee_ids}
        if employee_ids:
            placeholders = ','.join(['%s'] * len(employee_ids))
            cursor.execute(f"""
                SELECT employee_id, menu_item_id
                FROM newapp_usermenupermission
                WHERE employee_id IN ({placeholders})
            """, employee_ids)
            for emp_id, menu_id in cursor.fetchall():
                permissions_map.setdefault(emp_id, []).append(int(menu_id))

        for employee in employees:
            employee['permissions'] = permissions_map.get(employee['id'], [])

        cursor.execute("SELECT code FROM employee WHERE superuser = 0")
        existing_codes_raw = [r[0] for r in cursor.fetchall()]

        cursor.execute("""
            SELECT id, name, section
            FROM newapp_menuitem
            WHERE section != %s
            ORDER BY section, name
        """, ['settings'])
        menu_items = dictfetchall(cursor)

    menu_items_by_section = {}
    for item in menu_items:
        if item['name'] == 'Access Control':
            continue   # skip this row
        section = item['section']
        menu_items_by_section.setdefault(section, []).append(item)

    existing_employee_codes = json.dumps(existing_codes_raw, cls=DjangoJSONEncoder)

    return render(request, 'employee.html', {
        'employees': employees,
        'existing_employee_codes': existing_employee_codes,
        'menu_items_by_section': menu_items_by_section,
    })


def employee_add(request):
    if request.method == 'POST':
        from bray_app.services.employee_service import validate_employee_code, check_duplicate_code, insert_employee, update_employee_permissions
        
        employee_type = request.POST.get('employee_type')
        code = request.POST.get('employee_code', '').strip()
        name = request.POST.get('employee_name', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '')
        mobile = request.POST.get('mobile', '')
        status = request.POST.get('status', 'active')
        image = request.FILES.get('image')
        selected_permissions = request.POST.getlist('menu_items')

        # Enhanced validation
        if not employee_type:
            messages.error(request, 'Employee type is required.')
            return redirect('employee')
        
        code_error = validate_employee_code(code)
        if code_error:
            messages.error(request, code_error)
            return redirect('employee')
        
        if not name:
            messages.error(request, 'Employee name is required.')
            return redirect('employee')
        
        if not password:
            messages.error(request, 'Password is required.')
            return redirect('employee')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return redirect('employee')
        
        if not status or status not in ['active', 'inactive']:
            messages.error(request, 'Status is required and must be either active or inactive.')
            return redirect('employee')

        if check_duplicate_code(code):
            messages.error(request, 'This Employee Code already exists.')
            return redirect('employee')

        try:
            image_name = image.name if image else None
            new_employee_id = insert_employee(employee_type, code, name, password, email, mobile, image_name, status)
            
            if new_employee_id and selected_permissions:
                update_employee_permissions(new_employee_id, selected_permissions)
            
            messages.success(request, 'Employee added successfully.')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'Failed to add employee.')
            
    return redirect('employee')


def employee_edit(request, id):
    if request.method == 'POST':
        from bray_app.services.employee_service import validate_employee_code, check_duplicate_code, update_employee, update_employee_permissions
        
        employee_type = request.POST.get('employee_type')
        new_code = request.POST.get('employee_code', '').strip()
        name = request.POST.get('employee_name', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '')
        mobile = request.POST.get('mobile', '')
        status = request.POST.get('status', 'active')
        image = request.FILES.get('image')
        selected_permissions = request.POST.getlist('menu_items')

        # Enhanced validation
        if not employee_type:
            messages.error(request, 'Employee type is required.')
            return redirect('employee')
        
        code_error = validate_employee_code(new_code)
        if code_error:
            messages.error(request, code_error)
            return redirect('employee')
        
        if not name:
            messages.error(request, 'Employee name is required.')
            return redirect('employee')
        
        if password and len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return redirect('employee')
        
        if not status or status not in ['active', 'inactive']:
            messages.error(request, 'Status is required and must be either active or inactive.')
            return redirect('employee')

        if check_duplicate_code(new_code, exclude_id=id):
            messages.error(request, 'This Employee Code already exists.')
            return redirect('employee')

        try:
            image_name = image.name if image else None
            update_employee(id, employee_type, new_code, name, password, email, mobile, status, image_name)
            update_employee_permissions(id, selected_permissions)
            
            messages.success(request, 'Employee updated successfully.')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'Failed to update employee.')
            
        return redirect('employee')

    # fetch employee for edit form
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, employee_type, code, name, password, email, mobile, image FROM employee WHERE id=%s", [id])
        row = cursor.fetchone()
        employee = {
            'id': row[0],
            'employee_type': row[1],
            'code': row[2],
            'name': row[3],
            'password': row[4],
            'email': row[5],
            'mobile': row[6],
            'image': row[7],
        }

        cursor.execute("SELECT code FROM employee WHERE id != %s", [id])
        existing_codes = [r[0] for r in cursor.fetchall()]

    return render(request, 'employee_edit.html', {
        'employee': employee,
        'existing_employee_codes': existing_codes,
    })


def employee_delete(request, id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM employee WHERE id=%s", [id])

    messages.success(request, 'Employee deleted successfully.')
    return redirect('employee')



# Gauge Details 

def _parse_date_ymd(val):
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(val, "%d-%m-%Y").date()
        except Exception:
            return None


@permission_required("Gauge Details")
def gauge_details(request):
    gauges = []
    validation_errors = []

    with connection.cursor() as cursor:
        # Fetch gauge data - Order by ACTIVE_STATUS DESC (Enable=1 first), then STATION_ID, then INSTRUMENT_ID
        cursor.execute("""
            SELECT INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                   CAL_DUE_DATE, CAL_DONE_DATE,
                   ACTIVE_STATUS, STATION_ID, DUE_ALARM
            FROM gauge_details
            ORDER BY ACTIVE_STATUS DESC, STATION_ID, INSTRUMENT_ID
        """)
        rows = cursor.fetchall()

        # Fetch enabled instrument types
        cursor.execute("""
            SELECT INSTRUMENT_TYPE
            FROM instrument_categories
            WHERE INSTRUMENT_STATUS = 'ENABLE'
        """)
        instrument_types = [row[0] for row in cursor.fetchall()]

        for r in rows:
            cal_due_date = r[4]
            cal_done_date = r[5]
            errors = []

            # Strict validations
            if cal_due_date and cal_done_date:
                if cal_done_date > cal_due_date:
                    errors.append("Calibration done date cannot be after due date.")

            if cal_due_date:
                if cal_due_date < datetime.now().date():
                    errors.append("Calibration due date is in the past.")

            if not cal_done_date and cal_due_date:
                errors.append("Calibration done date is missing while due date exists.")

            # Build gauge dict
            gauges.append({
                'gauge_id': r[0],
                'gauge_ser_no': r[1],
                'range': r[2],
                'gauge_type': r[3],
                'cal_due_date': cal_due_date.strftime('%Y-%m-%d') if cal_due_date else '',
                'cal_done_date': cal_done_date.strftime('%Y-%m-%d') if cal_done_date else '',
                'active_status': r[6],
                'station_id': r[7],
                'due_alarm': r[8],
                'errors': errors,
            })

            if errors:
                validation_errors.append({
                    'gauge_id': r[0],
                    'errors': errors,
                })

    return render(request, 'gauge_details.html', {
        'gauges': gauges,
        'instrument_types': instrument_types,
        'validation_errors': validation_errors,
    })


@csrf_exempt
@permission_required("Gauge Details")
def gauge_save(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        # Extract all rows from form
        gauge_names = request.POST.getlist('station1_gauge_name[]')
        serials = request.POST.getlist('station1_serial[]')
        ranges = request.POST.getlist('station1_range[]')
        types = request.POST.getlist('station1_type[]')
        done_dates = request.POST.getlist('station1_done_date[]')
        due_dates = request.POST.getlist('station1_due_date[]')
        station_ids = request.POST.getlist('station1_id[]')
        statuses = request.POST.getlist('station1_status[]')
        instrument_ids = request.POST.getlist('station1_instrument_id[]')  # optional hidden field for updates

        now_ts = timezone.now()

        # First, validate for duplicate serial numbers within the form
        serial_map = {}
        for i in range(len(gauge_names)):
            serial = serials[i].strip()
            if serial:
                instrument_id = ''
                try:
                    instrument_id = instrument_ids[i].strip()
                except (IndexError, ValueError):
                    pass
                
                if serial in serial_map:
                    messages.error(request, f'Duplicate serial number "{serial}" detected. Please use unique serial numbers.')
                    return redirect('gauge_details')
                serial_map[serial] = (i, instrument_id)

        # Now validate against database for each serial number
        with connection.cursor() as cursor:
            for serial, (idx, current_id) in serial_map.items():
                if current_id:
                    # Check if another record has this serial number
                    cursor.execute(
                        "SELECT INSTRUMENT_ID FROM gauge_details WHERE INSTRUMENT_SER_NO=%s AND INSTRUMENT_ID != %s",
                        [serial, current_id]
                    )
                else:
                    # New record, check if serial already exists
                    cursor.execute(
                        "SELECT INSTRUMENT_ID FROM gauge_details WHERE INSTRUMENT_SER_NO=%s",
                        [serial]
                    )
                
                existing = cursor.fetchone()
                if existing:
                    messages.error(request, f'Serial number "{serial}" already exists in database. Please use a unique serial number.')
                    return redirect('gauge_details')

        # Check for empty new rows before processing
        for i in range(len(gauge_names)):
            try:
                instrument_id = instrument_ids[i].strip()
            except (IndexError, ValueError):
                instrument_id = ''
            
            # Skip validation for existing rows
            if instrument_id:
                continue
            
            # For new rows, check if they are empty
            serial = serials[i].strip() if i < len(serials) else ''
            rng = ranges[i].strip() if i < len(ranges) else ''
            gauge_type = types[i].strip() if i < len(types) else ''
            station_id = station_ids[i].strip() if i < len(station_ids) else ''
            
            # If all key fields are empty, show error
            if not (serial or rng or gauge_type or station_id):
                messages.error(request, 'Empty gauge details are not allowed. Please fill all required fields or remove empty rows.')
                return redirect('gauge_details')

        # Validate station-wise row count (max 10 ENABLED rows per station)
        station_counts = {}
        for i in range(len(gauge_names)):
            station_id_str = station_ids[i].strip() if i < len(station_ids) else ''
            status_str = statuses[i].strip().lower() if i < len(statuses) else ''
            
            # Only count if station is selected AND status is enable
            if station_id_str and status_str == 'enable':
                try:
                    station_id_int = int(station_id_str)
                    if station_id_int not in station_counts:
                        station_counts[station_id_int] = 0
                    station_counts[station_id_int] += 1
                except (ValueError, IndexError):
                    pass
        
        # Check if any station has more than 10 enabled rows
        for station_id_int, count in station_counts.items():
            if count > 10:
                station_name = f'Station {station_id_int}'
                messages.error(request, f'{station_name} has {count} enabled rows. Only 10 enabled rows are allowed per station.')
                return redirect('gauge_details')

        for i in range(len(gauge_names)):
            # Use existing INSTRUMENT_ID or generate new
            try:
                gauge_id = int(instrument_ids[i])
            except (IndexError, ValueError):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COALESCE(MAX(INSTRUMENT_ID), 0) + 1 FROM gauge_details")
                    gauge_id = cursor.fetchone()[0]

            gauge_name = gauge_names[i].strip()
            gauge_ser_no = serials[i].strip()
            rng = ranges[i].strip()
            gauge_type = types[i].strip()
            cal_done_date = _parse_date_ymd(done_dates[i])
            cal_due_date = _parse_date_ymd(due_dates[i])

            try:
                station_id = int(station_ids[i])
            except:
                station_id = 0

            active_status = 1 if statuses[i].strip().lower() == 'enable' else 0

            with connection.cursor() as cursor:
                # Check if the gauge exists
                cursor.execute("SELECT CAL_DUE_DATE FROM gauge_details WHERE INSTRUMENT_ID=%s", [gauge_id])
                row = cursor.fetchone()
                # prev_due = row[0] if row else None
                # due_alarm = 1 if (prev_due and cal_due_date and cal_due_date > prev_due) else 0

                if row:
                    # UPDATE existing
                    cursor.execute(
                        """
                        UPDATE gauge_details
                        SET INSTRUMENT_SER_NO=%s, `RANGE`=%s, INSTRUMENT_TYPE=%s,
                            CAL_DUE_DATE=%s, CAL_DONE_DATE=%s,
                            ACTIVE_STATUS=%s, STATION_ID=%s,
                            UPDATED_DATE=%s
                        WHERE INSTRUMENT_ID=%s
                        """,
                        [gauge_ser_no, rng, gauge_type,
                         cal_due_date, cal_done_date,
                         active_status, station_id,
                         now_ts, gauge_id]
                    )
                    
                    # Log UPDATE
                    cursor.execute(
                        """
                        INSERT INTO gauge_log_details (
                            INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                            CAL_DUE_DATE, CAL_DONE_DATE,
                            STATION_ID, CREATED_DATE
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [gauge_id, gauge_ser_no, rng, gauge_type,
                         cal_due_date, cal_done_date,
                         station_id, now_ts]
                    )
                else:
                    # INSERT new - skip empty rows
                    # Check if any required field has data
                    has_data = gauge_ser_no or rng or gauge_type or station_id
                    
                    if has_data:
                        cursor.execute(
                            """
                            INSERT INTO gauge_details (
                                INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                                CAL_DUE_DATE, CAL_DONE_DATE,
                                ACTIVE_STATUS, STATION_ID,
                                CREATED_DATE, UPDATED_DATE
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [gauge_id, gauge_ser_no, rng, gauge_type,
                             cal_due_date, cal_done_date,
                             active_status, station_id,
                             now_ts, now_ts]
                        )

                        # Log
                        cursor.execute(
                            """
                            INSERT INTO gauge_log_details (
                                INSTRUMENT_ID, INSTRUMENT_SER_NO, `RANGE`, INSTRUMENT_TYPE,
                                CAL_DUE_DATE, CAL_DONE_DATE,
                                STATION_ID, CREATED_DATE
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [gauge_id, gauge_ser_no, rng, gauge_type,
                             cal_due_date, cal_done_date,
                             station_id, now_ts]
                        )
        messages.success(request, 'Gauge details saved successfully.')
        # Redirect back to the same page
        return redirect('gauge_details')

    except Exception as e:
        return redirect('gauge_details')
        

@csrf_exempt
@permission_required("Gauge Details")
def gauge_delete(request, instrument_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM gauge_details WHERE INSTRUMENT_ID=%s", [instrument_id])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

# Test Type

@permission_required("Test Type")
def test_type(request):
    # ---------------- Get superuser level from session ----------------
    superuser_level = request.session.get('superuser')
    try:
        if superuser_level is None:
            superuser_level = 0
        else:
            superuser_level = int(superuser_level)
    except (ValueError, TypeError):
        superuser_level = 0
   
    # ---------------- Fetch test types - For superuser level 1, only show enabled test types ----------------
    with connection.cursor() as cursor:
        if superuser_level == 1:
            # For superuser level 1, only fetch enabled test types
            cursor.execute("""
                SELECT id, test_id, test_name, medium, category,Tolerance, status
                FROM test_type
                WHERE status = 'ENABLE'
                ORDER BY test_id
            """)
        else:
            # For other superuser levels, fetch all test types
            cursor.execute("""
                SELECT id, test_id, test_name, medium, category,Tolerance, status
                FROM test_type
                ORDER BY STATUS DESC, test_id
            """)
        test_types = cursor.fetchall()

    # ---------------- Fetch category list for dropdown ----------------
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME
            FROM category
            WHERE STATUS = 'ENABLE'
            ORDER BY CATEGORY_NAME
        """)
        category_list = [row[0] for row in cursor.fetchall()]

    # Add "NONE" option explicitly
    if "NONE" not in category_list:
        category_list.insert(0, "NONE")

    # ---------------- Handle POST updates ----------------
    if request.method == "POST":
        test_ids = request.POST.getlist("test_id[]")
        testnames = request.POST.getlist("testname[]")
        mediums = request.POST.getlist("medium[]")
        categories = request.POST.getlist("category[]")
        tolerances = request.POST.getlist("tolerance[]")
        statuses = request.POST.getlist("status[]")

        # ✅ Check for empty test names
        for i, testname in enumerate(testnames, start=1):
            if not testname.strip():
                messages.error(request, f'Test name cannot be empty at row {i}. Please enter a valid name.')
                return redirect("test_type")

        # ✅ Check for duplicate test names (case-insensitive)
        with connection.cursor() as cursor:
            # Create a set to track seen names (case-insensitive)
            seen_names = set()
           
            for i, (test_id, testname) in enumerate(zip(test_ids, testnames), start=0):
                test_id = int(test_id)  # Convert to int
                testname_lower = testname.strip().lower()
               
                # Check if duplicate within the same request
                if testname_lower in seen_names:
                    messages.error(request, f'Duplicate test name "{testname}" found. Please use unique names.')
                    return redirect("test_type")
               
                seen_names.add(testname_lower)
               
                # Check for duplicates in database (case-insensitive)
                cursor.execute("""
                    SELECT test_id, test_name
                    FROM test_type
                    WHERE LOWER(test_name) = %s AND test_id != %s
                """, [testname_lower, test_id])
               
                duplicate = cursor.fetchone()
                if duplicate:
                    duplicate_id, duplicate_name = duplicate
                    messages.error(request, f'Test name "{testname}" already exists (found as "{duplicate_name}"). Please use a unique name.')
                    return redirect("test_type")

        with connection.cursor() as cursor:
            for test_id, testname, medium, category,tolerance, status in zip(
                    test_ids, testnames, mediums, categories, tolerances, statuses):
               
                test_id = int(test_id)  # Convert to int

                # Initialize column variables
                pressure_column = None
                duration_column = None

                # Only fetch column names if category is not NONE
                if category != "NONE":
                    cursor.execute("""
                        SELECT PRESSURE_COLUMN_NAME, DURATION_COLUMN_NAME
                        FROM category
                        WHERE CATEGORY_NAME = %s
                    """, (category,))
                    row = cursor.fetchone()
                    if row:
                        pressure_column, duration_column = row

                # Update test_type safely
                cursor.execute("""
                    UPDATE test_type
                    SET test_name = %s,
                        medium = %s,
                        category = %s,
                        Tolerance = %s,
                        status = %s,
                        pre_col_name = %s,
                        dur_col_name = %s,
                        updated_at = NOW()
                    WHERE test_id = %s
                """, [testname, medium, category, tolerance, status, pressure_column, duration_column, test_id])

                messages.success(request, "Test Type details updated successfully!")
        return redirect("test_type")  # Reload page after update

    # ---------------- Prepare data for template ----------------
    data = [
        {
            "id": row[0],
            "test_id": row[1],
            "test_name": row[2],
            "medium": row[3],
            "category": row[4],
            "tolerance": row[5],
            "status": row[6],
        }
        for row in test_types
    ]

    return render(request, "test_type.html", {
        "categories": data,
        "category_list": category_list,
        "superuser_level": superuser_level
    })




@permission_required("Test Type")
def test_type(request):
    # ---------------- Get superuser level from session ----------------
    superuser_level = request.session.get('superuser')
    try:
        if superuser_level is None:
            superuser_level = 0
        else:
            superuser_level = int(superuser_level)
    except (ValueError, TypeError):
        superuser_level = 0
   
    # ---------------- Fetch test types - For superuser level 1, only show enabled test types ----------------
    with connection.cursor() as cursor:
        if superuser_level == 1:
            # For superuser level 1, only fetch enabled test types
            cursor.execute("""
                SELECT id, test_id, test_name, medium, category, Tolerance, status
                FROM test_type
                WHERE status = 'ENABLE'
                ORDER BY test_id
            """)
        else:
            # For other superuser levels, fetch all test types
            cursor.execute("""
                SELECT id, test_id, test_name, medium, category, Tolerance, status
                FROM test_type
                ORDER BY STATUS DESC, test_id
            """)
        test_types = cursor.fetchall()

    # ---------------- Fetch category list for dropdown ----------------
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_NAME
            FROM category
            WHERE STATUS = 'ENABLE'
            ORDER BY CATEGORY_NAME
        """)
        category_list = [row[0] for row in cursor.fetchall()]

    # Add "NONE" option explicitly
    if "NONE" not in category_list:
        category_list.insert(0, "NONE")

    # ---------------- Handle POST updates ----------------
    if request.method == "POST":
        test_ids = request.POST.getlist("test_id[]")
        testnames = request.POST.getlist("testname[]")
        mediums = request.POST.getlist("medium[]")
        categories = request.POST.getlist("category[]")
        tolerances = request.POST.getlist("tolerance[]")
        statuses = request.POST.getlist("status[]")

        # ✅ Check for empty test names
        for i, testname in enumerate(testnames, start=1):
            if not testname.strip():
                messages.error(request, f'Test name cannot be empty at row {i}. Please enter a valid name.')
                return redirect("test_type")

        # ✅ Check for empty tolerance when status is ENABLE
        for i, (status, tolerance) in enumerate(zip(statuses, tolerances), start=1):
            if status == 'ENABLE' and (not tolerance or str(tolerance).strip() == ''):
                messages.error(request, f'Tolerance cannot be empty when status is ENABLE at row {i}. Please enter a valid tolerance value.')
                return redirect("test_type")

        # ✅ Check for duplicate test names (case-insensitive)
        with connection.cursor() as cursor:
            # Create a set to track seen names (case-insensitive)
            seen_names = set()
           
            for i, (test_id, testname) in enumerate(zip(test_ids, testnames), start=0):
                test_id = int(test_id)  # Convert to int
                testname_lower = testname.strip().lower()
               
                # Check if duplicate within the same request
                if testname_lower in seen_names:
                    messages.error(request, f'Duplicate test name "{testname}" found. Please use unique names.')
                    return redirect("test_type")
               
                seen_names.add(testname_lower)
               
                # Check for duplicates in database (case-insensitive)
                cursor.execute("""
                    SELECT test_id, test_name
                    FROM test_type
                    WHERE LOWER(test_name) = %s AND test_id != %s
                """, [testname_lower, test_id])
               
                duplicate = cursor.fetchone()
                if duplicate:
                    duplicate_id, duplicate_name = duplicate
                    messages.error(request, f'Test name "{testname}" already exists (found as "{duplicate_name}"). Please use a unique name.')
                    return redirect("test_type")

        with connection.cursor() as cursor:
            for test_id, testname, medium, category, tolerance, status in zip(
                    test_ids, testnames, mediums, categories, tolerances, statuses):
               
                test_id = int(test_id)  # Convert to int

                # ✅ Handle empty tolerance values properly for FLOAT column
                if not tolerance or str(tolerance).strip() == '':
                    tolerance = None  # NULL for database
                else:
                    try:
                        tolerance = float(tolerance)
                    except (ValueError, TypeError):
                        tolerance = None

                # Initialize column variables
                pressure_column = None
                duration_column = None

                # Only fetch column names if category is not NONE
                if category != "NONE":
                    cursor.execute("""
                        SELECT PRESSURE_COLUMN_NAME, DURATION_COLUMN_NAME
                        FROM category
                        WHERE CATEGORY_NAME = %s
                    """, (category,))
                    row = cursor.fetchone()
                    if row:
                        pressure_column, duration_column = row

                # Update test_type safely
                cursor.execute("""
                    UPDATE test_type
                    SET test_name = %s,
                        medium = %s,
                        category = %s,
                        Tolerance = %s,
                        status = %s,
                        pre_col_name = %s,
                        dur_col_name = %s,
                        updated_at = NOW()
                    WHERE test_id = %s
                """, [testname, medium, category, tolerance, status, pressure_column, duration_column, test_id])

            messages.success(request, "Test Type details updated successfully!")
        return redirect("test_type")  # Reload page after update

    # ---------------- Prepare data for template ----------------
    data = [
        {
            "id": row[0],
            "test_id": row[1],
            "test_name": row[2],
            "medium": row[3],
            "category": row[4],
            "tolerance": row[5] if row[5] is not None else '',
            "status": row[6],
        }
        for row in test_types
    ]

    return render(request, "test_type.html", {
        "categories": data,
        "category_list": category_list,
        "superuser_level": superuser_level
    })

#     # ---------------- Get superuser level from session ----------------
#     superuser_level = request.session.get('superuser')
#     try:
#         if superuser_level is None:
#             superuser_level = 0
#         else:
#             superuser_level = int(superuser_level)
#     except (ValueError, TypeError):
#         superuser_level = 0
   
#     # ---------------- Fetch test types - For superuser level 1, only show enabled test types ----------------
#     with connection.cursor() as cursor:
#         if superuser_level == 1:
#             # For superuser level 1, only fetch enabled test types
#             cursor.execute("""
#                 SELECT id, test_id, test_name, medium, category, Tolerance, status
#                 FROM test_type
#                 WHERE status = 'ENABLE'
#                 ORDER BY test_id
#             """)
#         else:
#             # For other superuser levels, fetch all test types
#             cursor.execute("""
#                 SELECT id, test_id, test_name, medium, category, Tolerance, status
#                 FROM test_type
#                 ORDER BY STATUS DESC, test_id
#             """)
#         test_types = cursor.fetchall()

#     # ---------------- Fetch category list for dropdown ----------------
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT CATEGORY_NAME
#             FROM category
#             WHERE STATUS = 'ENABLE'
#             ORDER BY CATEGORY_NAME
#         """)
#         category_list = [row[0] for row in cursor.fetchall()]

#     # Add "NONE" option explicitly
#     if "NONE" not in category_list:
#         category_list.insert(0, "NONE")

#     # ---------------- Handle POST updates ----------------
#     if request.method == "POST":
#         test_ids = request.POST.getlist("test_id[]")
#         testnames = request.POST.getlist("testname[]")
#         mediums = request.POST.getlist("medium[]")
#         categories = request.POST.getlist("category[]")
#         tolerances = request.POST.getlist("tolerance[]")
#         statuses = request.POST.getlist("status[]")

#         # ✅ Check for empty test names
#         for i, testname in enumerate(testnames, start=1):
#             if not testname.strip():
#                 messages.error(request, f'Test name cannot be empty at row {i}. Please enter a valid name.')
#                 return redirect("test_type")

#         # ✅ Check for duplicate test names (case-insensitive)
#         with connection.cursor() as cursor:
#             # Create a set to track seen names (case-insensitive)
#             seen_names = set()
           
#             for i, (test_id, testname) in enumerate(zip(test_ids, testnames), start=0):
#                 test_id = int(test_id)  # Convert to int
#                 testname_lower = testname.strip().lower()
               
#                 # Check if duplicate within the same request
#                 if testname_lower in seen_names:
#                     messages.error(request, f'Duplicate test name "{testname}" found. Please use unique names.')
#                     return redirect("test_type")
               
#                 seen_names.add(testname_lower)
               
#                 # Check for duplicates in database (case-insensitive)
#                 cursor.execute("""
#                     SELECT test_id, test_name
#                     FROM test_type
#                     WHERE LOWER(test_name) = %s AND test_id != %s
#                 """, [testname_lower, test_id])
               
#                 duplicate = cursor.fetchone()
#                 if duplicate:
#                     duplicate_id, duplicate_name = duplicate
#                     messages.error(request, f'Test name "{testname}" already exists (found as "{duplicate_name}"). Please use a unique name.')
#                     return redirect("test_type")

#         with connection.cursor() as cursor:
#             for test_id, testname, medium, category, tolerance, status in zip(
#                     test_ids, testnames, mediums, categories, tolerances, statuses):
               
#                 test_id = int(test_id)  # Convert to int

#                 # ✅ Handle empty tolerance values properly for FLOAT column
#                 if not tolerance or str(tolerance).strip() == '':
#                     tolerance = None  # NULL for database
#                 else:
#                     try:
#                         tolerance = float(tolerance)
#                     except (ValueError, TypeError):
#                         tolerance = None

#                 # Initialize column variables
#                 pressure_column = None
#                 duration_column = None

#                 # Only fetch column names if category is not NONE
#                 if category != "NONE":
#                     cursor.execute("""
#                         SELECT PRESSURE_COLUMN_NAME, DURATION_COLUMN_NAME
#                         FROM category
#                         WHERE CATEGORY_NAME = %s
#                     """, (category,))
#                     row = cursor.fetchone()
#                     if row:
#                         pressure_column, duration_column = row

#                 # Update test_type safely
#                 cursor.execute("""
#                     UPDATE test_type
#                     SET test_name = %s,
#                         medium = %s,
#                         category = %s,
#                         Tolerance = %s,
#                         status = %s,
#                         pre_col_name = %s,
#                         dur_col_name = %s,
#                         updated_at = NOW()
#                     WHERE test_id = %s
#                 """, [testname, medium, category, tolerance, status, pressure_column, duration_column, test_id])

#             messages.success(request, "Test Type details updated successfully!")
#         return redirect("test_type")  # Reload page after update

#     # ---------------- Prepare data for template ----------------
#     data = [
#         {
#             "id": row[0],
#             "test_id": row[1],
#             "test_name": row[2],
#             "medium": row[3],
#             "category": row[4],
#             "tolerance": row[5] if row[5] is not None else '',
#             "status": row[6],
#         }
#         for row in test_types
#     ]

#     return render(request, "test_type.html", {
#         "categories": data,
#         "category_list": category_list,
#         "superuser_level": superuser_level
#     })
    
# Instrument type

@permission_required("Instrument Type")
def instrument_type(request):
    # Fetch all instrument types - Order by INSTRUMENT_STATUS DESC (ENABLE first), then INSTRUMENT_TYPE_ID
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT INSTRUMENT_TYPE_ID, INSTRUMENT_TYPE, INSTRUMENT_STATUS
            FROM instrument_categories
            ORDER BY INSTRUMENT_STATUS DESC, INSTRUMENT_TYPE_ID
        """)
        instrument_types = cursor.fetchall()

    if request.method == "POST":
        instrument_ids = request.POST.getlist("instrument_id[]")
        instrument_names = request.POST.getlist("instrument_name[]")
        statuses = request.POST.getlist("status[]")

        # ✅ Process each record - Insert new or Update existing
        with connection.cursor() as cursor:
            for instrument_id, instrument_name, status in zip(instrument_ids, instrument_names, statuses):
                instrument_name = instrument_name.strip()
                status = status.strip()
               
                # Skip empty rows
                if not instrument_name:
                    continue
               
                if instrument_id and instrument_id.strip():
                    # Update existing record
                    cursor.execute("""
                        UPDATE instrument_categories
                        SET INSTRUMENT_TYPE = %s,
                            INSTRUMENT_STATUS = %s,
                            UPDATED_DATE = NOW()
                        WHERE INSTRUMENT_TYPE_ID = %s
                    """, [instrument_name, status, instrument_id])
                else:
                    # Insert new record - calculate next INSTRUMENT_TYPE_ID
                    cursor.execute("SELECT COALESCE(MAX(INSTRUMENT_TYPE_ID), 0) + 1 FROM instrument_categories")
                    next_instrument_type_id = cursor.fetchone()[0]
                   
                    cursor.execute("""
                        INSERT INTO instrument_categories
                        (INSTRUMENT_TYPE_ID, INSTRUMENT_TYPE, INSTRUMENT_STATUS, CREATED_DATE, UPDATED_DATE)
                        VALUES (%s, %s, %s, NOW(), NOW())
                    """, [next_instrument_type_id, instrument_name, status])

        messages.success(request, "Instrument details saved successfully!")
        return redirect("instrument_type")  # Reload page after update

    #  Prepare data for template
    data = [
        {
            "id": row[0],
            "instrument_name": row[1],
            "status": row[2],
        }
        for row in instrument_types
    ]

    return render(request, "instrument_type.html", {"instrument_types": data})


@csrf_exempt
@permission_required("Instrument Type")
def instrument_type_delete(request, instrument_type_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Invalid method'}, status=405)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM instrument_categories WHERE INSTRUMENT_TYPE_ID=%s", [instrument_type_id])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def graph(request):
    return render(request, 'graph.html')

def vtr(request):
    return render(request, 'vtr.html')

def pdf(request):
    return render(request,'pdf_regenerate.html')


# User Permissions
def dictfetchall(cursor):
    """Return all rows from cursor as dicts"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def dictfetchone(cursor):
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if row:
        return dict(zip(columns, row))
    return None

def user_permissions_view(request):
    # Fetch non-superuser employees
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM employee WHERE superuser=0 ORDER BY name ASC")
        employees = dictfetchall(cursor)

    selected_employee = None
    selected_item_ids = []
    is_selected_superuser = False

    # Handle GET request for viewing permissions
    if request.method == 'GET' and 'user_id' in request.GET:
        employee_id = request.GET.get('user_id')
        if employee_id:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM employee WHERE id=%s", [employee_id])
                selected_employee = dictfetchone(cursor)

            if selected_employee and selected_employee['superuser']:
                messages.error(request, 'Cannot assign permissions to a superuser.')
                return redirect('user_permissions_view')

            # Fetch existing permissions
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT menu_item_id FROM newapp_usermenupermission
                    WHERE employee_id=%s
                """, [employee_id])
                selected_item_ids = [row['menu_item_id'] for row in dictfetchall(cursor)]

            is_selected_superuser = bool(selected_employee['superuser'])

    # Handle POST request for updating permissions
    if request.method == 'POST':
        employee_id = request.POST.get('user_id')
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM employee WHERE id=%s", [employee_id])
            selected_employee = dictfetchone(cursor)

        if selected_employee and selected_employee['superuser']:
            messages.error(request, 'Cannot assign permissions to a superuser.')
            return redirect('user_permissions_view')

        is_selected_superuser = bool(selected_employee['superuser'])

        selected_ids = request.POST.getlist('menu_items')

        # Delete existing permissions
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM newapp_usermenupermission WHERE employee_id=%s", [employee_id])

        # Insert new permissions
        with connection.cursor() as cursor:
            for item_id in selected_ids:
                if item_id:
                    cursor.execute("""
                        INSERT INTO newapp_usermenupermission (employee_id, menu_item_id)
                        VALUES (%s, %s)
                    """, [employee_id, item_id])

        messages.success(request, 'User permissions updated successfully!')
        return redirect('/user_permissions_view/')

    # Load menu items and group by section
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM newapp_menuitem")
        menu_items = dictfetchall(cursor)

    if selected_employee and not selected_employee['superuser']:
        menu_items = [item for item in menu_items if item['section'] != 'settings']

    # Group menu items by section
    menu_items_by_section = {}
    for item in menu_items:
        menu_items_by_section.setdefault(item['section'], []).append(item)

    context = {
        'users': employees,
        'selected_user': selected_employee,
        'selected_item_ids': list(map(int, selected_item_ids)),
        'menu_items_by_section': menu_items_by_section,
        'is_selected_superuser': is_selected_superuser,
    }

    return render(request, 'user_permissions.html', context)



@permission_required("Category")
def category(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT CATEGORY_ID, CATEGORY_NAME, STATUS
            FROM bray2.category
            ORDER BY STATUS DESC, CATEGORY_ID
        """)
        categories = cursor.fetchall()

        data = [
        {
            "id": row[0],
            "category_name": row[1],
            "status": row[2],
        }
        for row in categories
        ]
    return render(request, "category.html", {"categories": data})



def category_api(request):
    if request.method == "POST":
        body = request.body.decode("utf-8")
        data = json.loads(body)

        print("received data",data)

        # Receive list
        category_ids = data.get("category_ids", [])
        print("ids", category_ids)
        testnames = data.get("testnames", [])
        print("ids", testnames)
        statuses = data.get("statuses", [])
        print("ids", statuses)

        #Check for empty category names
        for i, testname in enumerate(testnames, start=1):
            if not testname.strip():
                messages.error(request, f'Category name cannot be empty at row {i}. Please enter a valid name.')
                return redirect("category")

        #Check for duplicate category names (case-insensitive)
        with connection.cursor() as cursor:
            # Create a set to track seen names (case-insensitive)
            seen_names = set()
            
            for i, (category_id, testname) in enumerate(zip(category_ids, testnames), start=0):
                category_id = int(category_id)  # Convert to int
                testname_lower = testname.strip().lower()
                
                # Check if duplicate within the same request
                if testname_lower in seen_names:
                    messages.error(request, f'Duplicate category name "{testname}" found. Please use unique names.')
                    return redirect("category")
                
                seen_names.add(testname_lower)
                
                # Check for duplicates in database (case-insensitive)
                cursor.execute("""
                    SELECT CATEGORY_ID, CATEGORY_NAME
                    FROM category
                    WHERE LOWER(CATEGORY_NAME) = %s AND CATEGORY_ID != %s
                """, [testname_lower, category_id])
                
                duplicate = cursor.fetchone()
                if duplicate:
                    duplicate_id, duplicate_name = duplicate
                    messages.error(request, f'Category name "{testname}" already exists (found as "{duplicate_name}"). Please use a unique name.')
                    return redirect("category")

        #Update each record
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

    return JsonResponse ({'status': 'success', 'message': 'Data Saved Successfully'})
    


def abrs(request):
    return render(request,'abrs.html')

def test_result(request):
    return render(request,'test_result.html')


def user_accounting(request):
    return render(request,'user_account.html')

def user_anable_disable(request):
    return render(request,'user_anable_disable.html')

def user_config(request):
    return render(request,'config2.html')

def livepage(request):
    return render(request,'livepage.html')

def dummy(request):
    return render(request, 'syncpage.html')


def station1(request):
    with connection.cursor() as cursor:
        cursor.execute("select name from valvesize")
        result = cursor.fetchall()  
        size = [row[0] for row in result]
        
        cursor.execute("select name from valveclass")
        result1 = cursor.fetchall()  
        valveclass = [row[0] for row in result1]
        
        cursor.execute("select name from shell_material")
        result2 = cursor.fetchall()  
        shellmaterial = [row[0] for row in result2]
        
        cursor.execute("select name from valve_type")
        result3 = cursor.fetchall()  
        valvetype = [row[0] for row in result3]
        
        cursor.execute("select name from employee")
        assembled = cursor.fetchall()  
        assembledby = [row[0] for row in assembled]
        
    return render(request,'station1_form.html',{'size':size,'class':valveclass,'shellmaterial':shellmaterial,'valvetype':valvetype,'assembledby':assembledby})


@csrf_exempt   
def getpressure_duration(request):
    if request.method == "POST":
        data = json.loads(request.body)

        size = data.get("size")
        valve_class = data.get("class")
        body = data.get("body")

        with connection.cursor() as cursor:
            # Initialize default values
            shell_duration = 0
            seat_duration = 0
            hydroair_duration = 0
            air_duration = 0
            shell_bar = 0
            seat_bar = 0
            Airshell_bar = 0
            Airseat_bar = 0
            
            cursor.execute("select shell,hydro_seat,shell_air,air from valvesize where name=%s",[size])
            result = cursor.fetchone()
            if result:
                shell_duration = result[0] or 0
                seat_duration = result[1] or 0
                hydroair_duration = result[2] or 0
                air_duration = result[3] or 0
              
            cursor.execute("select id from shell_material where name=%s",[body])   
            materialbody_result = cursor.fetchone()
            if materialbody_result is None:
                return JsonResponse({"status": "error", "message": "Shell material not found"})
            materialbody = materialbody_result[0]
            
            cursor.execute("select id from valveclass where name=%s",[valve_class])   
            valveclass_result = cursor.fetchone()
            if valveclass_result is None:
                return JsonResponse({"status": "error", "message": "Valve class not found"})
            valveclass_id = valveclass_result[0]
          
            
            cursor.execute("select hydro_seat,air_seat,shell_hydro,shell_air from newapp_classstandard where Class_id=%s and shellmaterial_id=%s",[valveclass_id,materialbody])
            pressure = cursor.fetchone()
            if pressure:
                shell_bar = pressure[0] or 0
                seat_bar = pressure[1] or 0
                Airshell_bar = pressure[2] or 0
                Airseat_bar = pressure[3] or 0
                
            return JsonResponse({"status":"success","shell_duration":shell_duration,
                                "seat_duration":seat_duration,"hydroair_duration":hydroair_duration,
                                "air_duration":air_duration,"shell_bar":shell_bar,
                                "seat_bar":seat_bar,"Airshell_bar":Airshell_bar,"Airseat_bar":Airseat_bar})
            
      

def user_accounting(request):
    with connection.cursor() as cursor:
       
        # Now try our actual query
        cursor.execute("""
            SELECT employee_code, employe_name, employee_type, last_login, last_logout
            FROM employee_login_logout_status
            ORDER BY id
        """)
        rows = cursor.fetchall()
       
        employees = [
            {
                'code': r[0],
                'name': r[1],
                'employee_type': r[2],
                'last_login': r[3],
                'last_logout': r[4],
            }
            for r in rows
        ]

    return render(request, 'user_account.html', {
        'employees': employees,
    })

@csrf_exempt
def save_station1(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            fields = [
               "size", "class", "body_material", "type", "customer", "assembledby", "pressureunit",
                "reportno", "testedby", "braypartno", "customer_po", "bray_order", "stem",
                "body1_partno", "body1_heatcode", "body1_material",
                "bottom_partno", "bottom_heatcode", "bottom_material",
                "dics_partno", "disc_heatcode", "disc_material",
                "seat_partno", "seat_heatcode", "seat_material",
                "stem_partno", "stem_heatcode", "stem_material",
                "Hydro_Shell_pressure", "Hydro_Shell_duration",
                "Hydro_Seat_P_pressure",  "Hydro_Seat_P_duration",
                "Hydro_Seat_N_pressure", "Hydro_Seat_N_duration",
                "Air_Shell_pressure","Air_Shell_duration",
                "Air_Seat_P_pressure", "Air_Seat_P_duration",
                "Air_Seat_N_pressure", "Air_Seat_N_duration",
                "station", "status"
            ]

            station_value = data.get('station', 'station1') 
            status_value = data.get('status', 'active')    

            values = [
                data.get(f) if f not in ["station", "status"] else station_value if f == "station" else status_value
                for f in fields
            ]

            with connection.cursor() as cursor:
                set_clause = ", ".join([f"{f} = %s" for f in fields] + ["cycle_complete = %s"])
                cursor.execute(
                    f"UPDATE station1_data SET {set_clause} WHERE id='1'",
                    values + [1]
                )

            return JsonResponse({"status": "success", "received": data})

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


@csrf_exempt
def save_station2(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            fields = [
                "size", "class", "body_material", "type", "customer", "assembledby", "pressureunit",
                "reportno", "testedby", "braypartno", "customer_po", "bray_order", "stem",
                "body1_partno", "body1_heatcode", "body1_material",
                "bottom_partno", "bottom_heatcode", "bottom_material",
                "dics_partno", "disc_heatcode", "disc_material",
                "seat_partno", "seat_heatcode", "seat_material",
                "stem_partno", "stem_heatcode", "stem_material",
                "Hydro_Shell_pressure", "Hydro_Shell_duration",
                "Hydro_Seat_P_pressure",  "Hydro_Seat_P_duration",
                "Hydro_Seat_N_pressure", "Hydro_Seat_N_duration",
                "Air_Shell_pressure","Air_Shell_duration",
                "Air_Seat_P_pressure", "Air_Seat_P_duration",
                "Air_Seat_N_pressure", "Air_Seat_N_duration",
                "station", "status"
            ]

            station_value = data.get('station', 'station2') 
            status_value = data.get('status', 'active')    

            values = [
                data.get(f) if f not in ["station", "status"] else station_value if f == "station" else status_value
                for f in fields
            ]

            with connection.cursor() as cursor:
                set_clause = ", ".join([f"{f} = %s" for f in fields] + ["cycle_complete = %s"])
                cursor.execute(
                    f"UPDATE station1_data SET {set_clause} WHERE id='2'",
                    values + [1]
                )

            return JsonResponse({"status": "success", "received": data})

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


def stationnew(request):
    with connection.cursor() as cursor:
        cursor.execute("select SIZE_NAME from valvesize")
        result = cursor.fetchall()  
        size = [row[0] for row in result]
        
        cursor.execute("select CLASS_NAME from valveclass")
        result1 = cursor.fetchall()  
        valveclass = [row[0] for row in result1]
        
        cursor.execute("select SHELL_MATERIAL_NAME from shell_material")
        result2 = cursor.fetchall()  
        shellmaterial = [row[0] for row in result2]
        
        cursor.execute("select TYPE_NAME from valve_type")
        result3 = cursor.fetchall()  
        valvetype = [row[0] for row in result3]
        
        
              
    return render(request,'stationnew.html',{'size':size,'class':valveclass,'shellmaterial':shellmaterial,'valvetype':valvetype })

@csrf_exempt
def disable_indb(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            fieldname = data.get('field_name')
            newValue = data.get('newValue')

            allowed_fields = ['shell_disable', 'hydro_seat_p_disable', 'hydro_seat_N_disable', 'Air_shell_disable', 'Air_seat_P_disable', 'Air_seat_N_disable']

            if fieldname not in allowed_fields:
                return JsonResponse({"status": "error", "message": "Invalid field name provided."}, status=400)
            
            if(newValue == True):
                with connection.cursor() as cursor:
                    query = f"UPDATE station1_data SET {fieldname}=%s WHERE id=%s"
                    cursor.execute(query, ["Disabled", 1])
            else:
                with connection.cursor() as cursor:
                    query = f"UPDATE station1_data SET {fieldname}=%s WHERE id=%s"
                    cursor.execute(query, ["Enabled", 1])
                
            return JsonResponse({"status": "success", "message": "Field updated successfully."})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    else:
         return JsonResponse({"status": "error", "message": "Invalid request method. Only POST is allowed."}, status=405)
     


@csrf_exempt
def disable2_indb(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            fieldname = data.get('field_name')
            newValue = data.get('newValue')

            allowed_fields = ['shell_disable', 'hydro_seat_p_disable', 'hydro_seat_N_disable', 'Air_shell_disable', 'Air_seat_P_disable', 'Air_seat_N_disable']

            if fieldname not in allowed_fields:
                return JsonResponse({"status": "error", "message": "Invalid field name provided."}, status=400)
            
            if(newValue == True):
                with connection.cursor() as cursor:
                    query = f"UPDATE station1_data SET {fieldname}=%s WHERE id=%s"
                    cursor.execute(query, ["Disabled", 2])
            else:
                with connection.cursor() as cursor:
                    query = f"UPDATE station1_data SET {fieldname}=%s WHERE id=%s"
                    cursor.execute(query, ["Enabled", 2])
                
            return JsonResponse({"status": "success", "message": "Field updated successfully."})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    else:
         return JsonResponse({"status": "error", "message": "Invalid request method. Only POST is allowed."}, status=405)
     

FIELD_MAP = {
    "hydroshell_s1": "Hydro Shell Test",
    "hydroshell_s2": "Hydro Shell Test",
    
    "hydroseat_p_s1": "Hydro Seat P Test",
    "hydroseat_p_s2": "Hydro Seat P Test",
    
    "hydroseat_n_s1": "Hydro Seat N Test",
    "hydroseat_n_s2": "Hydro Seat N Test",
    
    "airshell_s1": "Air Shell Test",
    "airshell_s2": "Air Shell Test",
    
    "airseat_p_s1": "Air Seat P Test",
    "airseat_p_s2": "Air Seat P Test",
    
    "airseat_n_s1": "Air Seat N Test",
    "airseat_n_s2": "Air Seat N Test",
    
    "graph_toggle": "Graph PDF Report",
    "pdf_toggle": "VTR PDF Report",
    "csv_toggle": "VTR CSV Report",
    "sync": "Sync"
}

@csrf_exempt
def toggle_field(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            field_code = data.get("field")
            status = data.get("status")
            print('field_code',field_code)

            field_name = FIELD_MAP.get(field_code)
            if not field_name:
                return JsonResponse({"error": "Unknown field"}, status=400)


            status_value = "Enabled" if status else "Disabled"

            with connection.cursor() as cursor:
                if field_code.endswith("_s1"):
                    column_name = "station_1"
                    cursor.execute(
                        f"UPDATE settings SET {column_name} = %s WHERE Field_names = %s",
                        [status_value, field_name]
                    )
                elif field_code.endswith("_s2"):
                    column_name = "station_2"
                    cursor.execute(
                        f"UPDATE settings SET {column_name} = %s WHERE Field_names = %s",
                        [status_value, field_name]
                    )
                elif field_code in ["graph_toggle", "pdf_toggle", "csv_toggle", "sync"]:
                    column_name = "status"
                    cursor.execute(
                        "UPDATE settings SET status = %s WHERE Field_names = %s",
                        [status_value, field_name]
                    )
                else:
                    return JsonResponse({"error": "Unknown station for field"}, status=400)

            return JsonResponse({"success": True, "field": field_name, "column": column_name, "status": status_value})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)




def inactive_station1(request):    
    with connection.cursor() as cursor:
        cursor.execute("update station1_data set status='inactive' where id=1")
        cursor.execute("""
    UPDATE station1_data 
    SET 
        shell_disable = 'Enabled',
        hydro_seat_p_disable = 'Enabled',
        hydro_seat_N_disable = 'Enabled',
        Air_shell_disable = 'Enabled',
        Air_seat_P_disable = 'Enabled',
        Air_seat_N_disable = 'Enabled'
    WHERE id = 1
""")

        return JsonResponse({"status":"success"})
    return JsonResponse({"status":"failure"})

def inactive_station2(request):    
    with connection.cursor() as cursor:
        cursor.execute("update station1_data set status='inactive' where id=2")
        cursor.execute("""
    UPDATE station1_data 
    SET 
        shell_disable = 'Enabled',
        hydro_seat_p_disable = 'Enabled',
        hydro_seat_N_disable = 'Enabled',
        Air_shell_disable = 'Enabled',
        Air_seat_P_disable = 'Enabled',
        Air_seat_N_disable = 'Enabled'
    WHERE id = 2
""")
        return JsonResponse({"status":"success"})
    return JsonResponse({"status":"failure"})


@csrf_exempt
def get_pressure(request):
    try:
        if request.method == "POST":
            body = json.loads(request.body)
            test_id = body.get("id")

            if not test_id:
                return JsonResponse({"status": "failure", "message": "Missing test ID"})

            with connection.cursor() as cursor:
                cursor.execute("SELECT  pressure FROM station WHERE id = %s", [test_id])
                row = cursor.fetchone()

            if row:
                pressure = row[0]
                return JsonResponse({"status": "success", "pressure": pressure})
            else:
                return JsonResponse({"status": "failure", "message": "No record found"})

        return JsonResponse({"status": "failure", "message": "Invalid method"})

    except Exception as e:
        print("Error in get_pressure:", e)
        return JsonResponse({"status": "failure", "message": str(e)})        

def check_status(request):
    try:
        with connection.cursor() as cursor:
            # Fetch statuses
            cursor.execute("SELECT status FROM station1_data WHERE id=1")
            station1_status = cursor.fetchone()[0].lower()

            cursor.execute("SELECT status FROM station1_data WHERE id=2")
            station2_status = cursor.fetchone()[0].lower()

            cursor.execute("SELECT status FROM settings WHERE Field_names='Sync'")
            sync_status = cursor.fetchone()[0].lower()

        # Default redirect
        redirect_url = "/livepage"

        # ---- Logic ----
        if sync_status == 'enabled':
            if station1_status == 'active' and station2_status == 'active':
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT class, size, body_material, type, pressureunit 
                        FROM station1_data WHERE id=1
                    """)
                    station1_data = cursor.fetchone()

                    cursor.execute("""
                        SELECT class, size, body_material, type, pressureunit 
                        FROM station1_data WHERE id=2
                    """)
                    station2_data = cursor.fetchone()

                # Compare both sets of data
                if station1_data == station2_data:
                    # redirect_url = "/syncpage"
                    redirect_url = "/dummy"
                else:
                    return JsonResponse({
                        "status": "failure",
                        "message": "Station 1 and Station 2 values do not match."
                    })

            elif station1_status == 'active' or station2_status == 'active':
                redirect_url = "/dummy"

        else:
            redirect_url = "/livepage"

        # ✅ Final consistent return
        return JsonResponse({
            "status": "success",
            "redirect_url": redirect_url,
            "station1_status": station1_status,
            "station2_status": station2_status
        })

    except Exception as e:
        print("Error in check_status:", e)
        return JsonResponse({"status": "failure"})
    


def getStation1_values(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT size, class, body_material, testedby, assembledby 
                FROM station1_data 
                WHERE id = 1
            """)
            row = cursor.fetchone()

        if row:
            size, cls, body_material, testedby, assembledby = row

            data = {
                "size": size,
                "class": cls,
                "body": body_material,
                "testedby": testedby,
                "assembledby": assembledby
            }

            return JsonResponse({"status": "success", "data": data})
        else:
            return JsonResponse({
                "status": "failure",
                "message": "No data found for Station 1."
            })

    except Exception as e:
        print("Error in getStation1_values:", e)
        return JsonResponse({
            "status": "failure",
            "message": str(e)
        })
    
def getStation2_values(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT size, class, body_material, testedby , assembledby
                FROM station1_data 
                WHERE id = 2
            """)
            row = cursor.fetchone()

        if row:
            # ✅ Pythonic tuple unpacking
            size, cls, body_material, testedby, assembledby = row

            data = {
                "size": size,
                "class": cls,
                "body": body_material,
                "testedby": testedby,
                "assembledby": assembledby
            }

            return JsonResponse({"status": "success", "data": data})
        else:
            return JsonResponse({
                "status": "failure",
                "message": "No data found for Station 1."
            })

    except Exception as e:
        print("Error in getStation1_values:", e)
        return JsonResponse({
            "status": "failure",
            "message": str(e)
        })



@csrf_exempt
def get_pressure_data1(request):
    global actual_pressure, TestleadSmartsyncx, timer_status
    
    try:
        
        value = TestleadSmartsyncx.read_holding_registers(2020,1).registers[0]
        timerStatus = TestleadSmartsyncx.read_holding_registers(2023,1).registers[0]
        actual_pressure = value

        with connection.cursor() as cursor:
            cursor.execute(""" 
                            INSERT INTO livepage1_data (pressure_value, timer_status, timestamp)
                        VALUES (%s, %s, %s)""",[value, timerStatus, datetime.now()])
            
        
        
        print(f"get_pressure_data1: pressure={value}, timerStatus={timerStatus}")
    
        return JsonResponse({
            "connected": True,
            "actualPressure1": value,
            "timerStatus": timerStatus
        })

    except Exception as e:
        print ("Error in get_pressure_data1:", e)
        return JsonResponse({"connected": False, "error": str(e)})
    




value = None


@csrf_exempt
def get_pressure_data(request):
    global value
    print("global value:", value)
    try:
        actual_pressure = float(value)
        if actual_pressure is None or actual_pressure != actual_pressure:  # NaN check
            actual_pressure = 0
    except Exception:
        actual_pressure = 0
    return JsonResponse({
        "connected": True,
        "actualPressure": actual_pressure,
    })


def get_stored_pressure_data(request):
    """Return last N records for plotting"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT timestamp, pressure_value
            FROM livepage1_data
            ORDER BY timestamp DESC
            LIMIT 500
        """)
        rows = cursor.fetchall()

    result = [{"time": r[0].strftime("%H:%M:%S"), "pressure": r[1]} for r in rows[::-1]]
    return JsonResponse({"status": "success", "data": result})


# Settings and Configuration 

def get_hmi_abrs(request):
    global TestleadSmartsyncx
    abrs_connection = 0
    
    if TestleadSmartsyncx is None or not TestleadSmartsyncx.connect():
        hmi_status = 0
        
        with connection.cursor() as cursor:
            cursor.execute("UPDATE configuration_table SET HMI_CONNECTION='Disabled' WHERE id=1")
    else:
        hmi_status = 1
        with connection.cursor() as cursor:
            cursor.execute("UPDATE configuration_table SET HMI_CONNECTION='Enabled' WHERE id=1")
    
    if abrs_connection == 0: 
        with connection.cursor() as cursor:
            cursor.execute("UPDATE configuration_table SET ABRS_CONNECTION='Disabled' WHERE id=1")
    else:
        abrs_connection = 1
        with connection.cursor() as cursor:
            cursor.execute("UPDATE configuration_table SET ABRS_CONNECTION='Enabled' WHERE id=1")
            
    return JsonResponse({"hmi_connection": hmi_status, "abrs_connection": abrs_connection})

# graph toggle

@csrf_exempt
def update_graph_toggle(request):
    data = json.loads(request.body)
    status = data.get("graph_toggle")

    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET GRAPH_PDF_REPORT=%s WHERE ID=1", [status])

    return JsonResponse({"graph_report": status})

@csrf_exempt
def update_pdf_toggle(request):
    data = json.loads(request.body)
    status = data.get("pdf_toggle")

    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET VTR_PDF_REPORT=%s WHERE ID=1", [status])

    return JsonResponse({"pdf_report": status})

@csrf_exempt
def update_csv_toggle(request):
    data = json.loads(request.body)
    status = data.get("csv_toggle")

    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET VTR_CSV_REPORT=%s WHERE ID=1", [status])

    return JsonResponse({"csv_report": status})

@csrf_exempt
def update_backup_toggle(request):
    data = json.loads(request.body)
    status = data.get("backup_toggle")

    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET AUTO_DB_BACKUP=%s WHERE ID=1", [status])

    return JsonResponse({"auto_backup": status})

@csrf_exempt
def get_graph_toggle(request):        
    with connection.cursor() as cursor:
        cursor.execute("SELECT GRAPH_PDF_REPORT,VTR_PDF_REPORT,VTR_CSV_REPORT,REPORT_PATH,AUTO_DB_BACKUP FROM configuration_table WHERE ID=1")
        report = cursor.fetchone()
        if report:
            all_reports = {
                "graph_pdf_report": report[0],
                "vtr_pdf_report": report[1],
                "vtr_csv_report": report[2],
                "report_path": report[3],
                "auto_db_backup": report[4]
            }
        return JsonResponse({"status": "success", "all_reports": all_reports})
    return JsonResponse({"status": "failure", "message": "No record found"})
  
@csrf_exempt
def save_report_path(request):
    data = json.loads(request.body)
    report_path = data.get("report_path")

    with connection.cursor() as cursor:
        cursor.execute("UPDATE configuration_table SET REPORT_PATH=%s WHERE ID=1", [report_path])
        cursor.commit()

    return JsonResponse({"report_path": report_path})

@csrf_exempt
def save_abrs_field(request):
    data = json.loads(request.body)
    field = data.get("field")
    value = data.get("value")

    allowed_fields = [
        "DRIVING_TORQUETEST_OBSERVED",
        "PUMP_TORQUETEST_OBSERVED",
        "VALVE_CYCLESTEST_PERFORMED",
        "HP_SHELL_WT_DUR",
        "VE1_PRESSURE_SHIFFERED_SEAT_WT_DUR",
        "VE1_PRESSURELOW_PRTD_UPPERLAST_WT_DUR",
        "LP_PREFERRED_SEAT_W_TOOLEDTEST_DUR",
        "LP_SEAT_REGIONTEST_DUR",
        "VE1_PRESSURESHELL_WT",
        "VE1_PRESSURE_SHIFFEREDSEAT_WT",
        "VE1_PRESSURELOW_PRTD_UPPERSTART_WT",
        "LP_PREFERRED_SEATAPPROVED_FLOWTEST_AIR",
        "LP_SEATAREA_REGIONTEST_AIR"
    ]

    if field not in allowed_fields:
        return JsonResponse({"status": "error", "message": "Invalid field"})

    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE configuration_table SET {field}=%s WHERE ID=1", [value])

    return JsonResponse({"status": "success", "saved_field": field})

@csrf_exempt
def get_abrs_values(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                DRIVING_TORQUETEST_OBSERVED,
                PUMP_TORQUETEST_OBSERVED,
                VALVE_CYCLESTEST_PERFORMED,
                HP_SHELL_WT_DUR,
                VE1_PRESSURE_SHIFFERED_SEAT_WT_DUR,
                VE1_PRESSURELOW_PRTD_UPPERLAST_WT_DUR,
                LP_PREFERRED_SEAT_W_TOOLEDTEST_DUR,
                LP_SEAT_REGIONTEST_DUR,
                VE1_PRESSURESHELL_WT,
                VE1_PRESSURE_SHIFFEREDSEAT_WT,
                VE1_PRESSURELOW_PRTD_UPPERSTART_WT,
                LP_PREFERRED_SEATAPPROVED_FLOWTEST_AIR,
                LP_SEATAREA_REGIONTEST_AIR
            FROM configuration_table
            WHERE id = 1
        """)
        row = cursor.fetchone()

    fields = [
        "DRIVING_TORQUETEST_OBSERVED",
        "PUMP_TORQUETEST_OBSERVED",
        "VALVE_CYCLESTEST_PERFORMED",
        "HP_SHELL_WT_DUR",
        "VE1_PRESSURE_SHIFFERED_SEAT_WT_DUR",
        "VE1_PRESSURELOW_PRTD_UPPERLAST_WT_DUR",
        "LP_PREFERRED_SEAT_W_TOOLEDTEST_DUR",
        "LP_SEAT_REGIONTEST_DUR",
        "VE1_PRESSURESHELL_WT",
        "VE1_PRESSURE_SHIFFEREDSEAT_WT",
        "VE1_PRESSURELOW_PRTD_UPPERSTART_WT",
        "LP_PREFERRED_SEATAPPROVED_FLOWTEST_AIR",
        "LP_SEATAREA_REGIONTEST_AIR"
    ]

    data = dict(zip(fields, row))

    return JsonResponse(data)

def set_test_mode(request):
    mode = request.GET.get('mode', 'manual')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE sync_nonsync_table SET TEST_MODE=%s WHERE ID=1", [mode])
    return JsonResponse({"status": "success", "mode": mode})



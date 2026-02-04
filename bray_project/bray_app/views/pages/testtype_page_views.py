from django.shortcuts import render
from bray_app.decorators import permission_required
from django.db import connection
from django.contrib import messages
from django.shortcuts import render, redirect
from bray_app.services.testtype_service import *

@permission_required("Test Type")
def testtype_page(request):   
    test_types = getall_testtype()

    # ---------------- Fetch category list for dropdown ----------------
    category_list = get_enabled_categories()

    # Add "NONE" option explicitly
    if "NONE" not in category_list:
        category_list.insert(0, "NONE")

    # ---------------- Handle POST updates ----------------
    if request.method == "POST":
        test_ids = request.POST.getlist("test_id[]")
        testnames = request.POST.getlist("testname[]")
        mediums = request.POST.getlist("medium[]")
        categories = request.POST.getlist("category[]")
        statuses = request.POST.getlist("status[]")

        # ✅ Check for empty test names
        for i, testname in enumerate(testnames, start=1):
            if not testname.strip():
                messages.error(request, f'Test name cannot be empty at row {i}. Please enter a valid name.')
                return redirect("testtype")

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
                    return redirect("testtype")

        with connection.cursor() as cursor:
            for test_id, testname, medium, category, status in zip(
                    test_ids, testnames, mediums, categories, statuses):
               
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
                        status = %s,
                        pre_col_name = %s,
                        dur_col_name = %s,
                        updated_at = NOW()
                    WHERE test_id = %s
                """, [testname, medium, category, status, pressure_column, duration_column, test_id])

                messages.success(request, "Test Type details updated successfully!")
        return redirect("testtype")  # Reload page after update

    # ---------------- Prepare data for template ----------------
    data = [
        {
            "test_id": row[0],
            "test_name": row[1],
            "medium": row[2],
            "category": row[3],
            "status": row[4]
        }
        for row in test_types
    ]

    return render(request, "test_type.html", {
        "categories": data,
        "category_list": category_list
    })


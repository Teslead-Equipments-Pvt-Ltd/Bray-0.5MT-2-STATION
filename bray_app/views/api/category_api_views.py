from django.http import JsonResponse
from bray_app.decorators import permission_required
import json
from django.contrib import messages
from django.db import connection
from django.shortcuts import render, redirect
from bray_app.services.category_services import check_duplicate_category, update_category




def api_category_update(request):
    if request.method == "GET":
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
        return JsonResponse({"status": "success", "categories": data})

    if request.method == "POST":
        body = request.body
        data = json.loads(body)

        # Receive list
        category_ids = data.get("category_ids", [])
        testnames = data.get("testnames", [])
        statuses = data.get("statuses", [])
        

        #Check for empty category names
        for i, testname in enumerate(testnames, start=1):
            if not testname.strip():
                return JsonResponse({
                    "status": "error",
                    "message": f"Category name cannot be empty at row {i}."
                })
            
        seen_names = set()
        for name in testnames:
            name_lower = name.strip().lower()   
            if name_lower in seen_names:
                return JsonResponse({
                    "status": "error",
                    "message": f'Duplicate category name "{name}" found in input.'
                })
            seen_names.add(name_lower)

        for category_id, name in zip(category_ids, testnames):
            if check_duplicate_category(category_id, name):
                return JsonResponse({
                    "status": "error",
                    "message": f'Category name "{name}" already exists in database.'
                })
                        
        update_category(category_ids, testnames, statuses)
        return JsonResponse ({'status': 'success', 'message': 'Data Saved Successfully', "success":True})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method', "success":False}, status=405 )
    





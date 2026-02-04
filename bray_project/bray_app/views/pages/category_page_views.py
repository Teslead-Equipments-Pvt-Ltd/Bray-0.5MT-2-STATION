from django.shortcuts import render, redirect
from bray_app.decorators import permission_required
from django.db import connection


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







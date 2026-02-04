from django.shortcuts import render
from bray_app.decorators import permission_required
from bray_app.services.valvetype_service import get_all_valve_types,get_superuser
from django.utils.safestring import mark_safe
import json
from django.db import connection

@permission_required("Valve Type")
def valve_type_page(request):
    # Get all valve types data
    data = get_all_valve_types()
    
    # Prepare data for template
    valve_types = data['valve_types']
    test_types = data['test_types']
    existing_codes = mark_safe(json.dumps(data['existing_codes']))
    existing_names = mark_safe(json.dumps(data['existing_names']))
    
    # Determine superuser level: prefer session value, fall back to DB lookup by username
    superuser_level = request.session.get('superuser')
    try:
        if superuser_level is None:
            username = request.session.get('username')
            if username:
                try:
                    row = get_superuser(username)
                    if row and row[0] is not None:
                        superuser_level = int(row[0])
                    else:
                        superuser_level = 0
                except Exception:
                    superuser_level = 0
            else:
                superuser_level = 0
        else:
            superuser_level = int(superuser_level)
    except (ValueError, TypeError):
        superuser_level = 0
    
    return render(request, "valve_type.html", {
        'valve_types': valve_types,
        'test_types': test_types,
        'existing_codes': existing_codes,
        'existing_names': existing_names,
        'superuser_level': superuser_level
    })
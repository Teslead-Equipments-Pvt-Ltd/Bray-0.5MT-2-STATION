from django.db import connection

def user_menu_context(request):
    sectioned_menu = {
        'master': [],
        'settings': [],
        'report': [],
        'users': [],
        'ABRS': []
    }

    username = request.session.get('username')
    superuser_level = request.session.get('superuser')
    
    # Convert superuser_level to int for comparison (handle None, string, int)
    try:
        if superuser_level is None:
            superuser_level = 0
        else:
            superuser_level = int(superuser_level)
    except (ValueError, TypeError):
        superuser_level = 0
    
    # Check if user is superuser (level 1 or 2)
    is_superuser = superuser_level in [1, 2]
    # Check if user is superuser level 2 (highest level - sees everything)
    is_superuser_2 = superuser_level == 2

    # Check if all categories are disabled
    all_categories_disabled = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM category WHERE STATUS = 'ENABLE'
            """)
            enabled_count = cursor.fetchone()[0]
            all_categories_disabled = enabled_count == 0
    except Exception:
        all_categories_disabled = False

    if username:
        with connection.cursor() as cursor:
            # ✅ Check if employee exists
            cursor.execute("SELECT id FROM employee WHERE name = %s", [username])
            row = cursor.fetchone()

            if row:
                employee_id = row[0]

                if is_superuser_2:
                    # Superuser level 2: Get all menu items (shows everything)
                    cursor.execute("SELECT DISTINCT id, name, section FROM newapp_menuitem")
                    menu_items = cursor.fetchall()
                elif superuser_level == 1:
                    # Superuser level 1: Get all menu items (Category/Test Type will be filtered below)
                    cursor.execute("SELECT DISTINCT id, name, section FROM newapp_menuitem")
                    menu_items = cursor.fetchall()
                else:
                    # Superuser level 0: Check if user has any permissions configured
                    cursor.execute("""
                        SELECT COUNT(*) FROM newapp_usermenupermission WHERE employee_id = %s
                    """, [employee_id])
                    total_permissions = cursor.fetchone()[0]
                    
                    if total_permissions == 0:
                        # No permissions configured, show nothing (only Dashboard and Logout will be visible)
                        menu_items = []
                    else:
                        # Get only menu items allowed for this employee (use DISTINCT to avoid duplicates)
                        cursor.execute("""
                            SELECT DISTINCT m.id, m.name, m.section
                            FROM newapp_menuitem m
                            INNER JOIN newapp_usermenupermission ump ON ump.menu_item_id = m.id
                            WHERE ump.employee_id = %s
                        """, [employee_id])
                        menu_items = cursor.fetchall()
                
                # Track added items to prevent duplicates
                added_items = set()

                # menu_items → list of tuples (id, name, section)
                for item in menu_items:
                    item_id, item_name, item_section = item

                    # Skip if already added
                    if item_id in added_items:
                        continue
                    added_items.add(item_id)

                    # Hide specific items for superuser level 1
                    if superuser_level == 1 and item_name in ["Category", "Test Type", "Instrument Type", "CategoryInstrument", "TypeTest"]:
                        continue

                    # Map items to the correct sections that the template expects
                    master_items = ['Standard', 'Valve Size', 'Valve Class', 'Valve Type', 'Shell Material', 'Gauge Details', 'Alarm', 'Category', 'CategoryInstrument', 'Instrument Type', 'Test Type', 'TypeTest']
                    
                    if item_name in master_items:
                        sectioned_menu['master'].append({
                            'id': item_id,
                            'name': item_name,
                            'section': item_section
                        })
                    elif item_section.lower() == 'report' or item_name in ['Graph']:
                        sectioned_menu['report'].append({
                            'id': item_id,
                            'name': item_name,
                            'section': item_section
                        })
                    elif item_section.lower() == 'abrs' or item_name in ['ABRS']:
                        sectioned_menu['ABRS'].append({
                            'id': item_id,
                            'name': item_name,
                            'section': item_section
                        })
                    elif item_section.lower() == 'settings' or item_name in ['Settings']:
                        sectioned_menu['settings'].append({
                            'id': item_id,
                            'name': item_name,
                            'section': item_section
                        })
                    elif item_name in ['Employee', 'Access Control']:
                        sectioned_menu['users'].append({
                            'id': item_id,
                            'name': item_name,
                            'section': item_section
                        })

    return {
        'sectioned_menu': sectioned_menu,
        'username': username,
        'all_categories_disabled': all_categories_disabled,
        'superuser_level': superuser_level
    }
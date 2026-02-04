from django.shortcuts import render
from bray_app.decorators import login_required
from bray_app.services.form_service import get_valve_size,get_valve_class, get_valve_standard,get_valve_type,get_shell_material,get_assemblers,get_testers

@login_required
def form_page(request):
    valve_standards = get_valve_standard()
    valve_sizes = get_valve_size()
    valve_classes = get_valve_class()
    valve_types = get_valve_type()
    shell_materials = get_shell_material()
    assemblers = get_assemblers()  # Approver type employees
    testers = get_testers()        # Tester type employees

    context = {
        "valve_standards": valve_standards,
        "valve_sizes": valve_sizes,
        "valve_classes": valve_classes,
        "valve_types": valve_types,
        "shell_materials": shell_materials,
        "assemblers": assemblers,
        "testers": testers
    }

    return render(request, "form.html", context)


    
from django.urls import path
from bray_app.views.api.shell_material_api_views import (
    shell_get_all_api, shell_get_one_api,
    shell_add_api, shell_edit_api, shell_delete_api,
    shell_meta_api, bulk_delete_shell_materials_api
)

urlpatterns = [
    path("shell-material/meta/", shell_meta_api),
    path("shell-material/", shell_get_all_api),
    path("shell-material/<int:material_id>/", shell_get_one_api),
    path("shell-material/add/", shell_add_api),
    path("shell-material/edit/<int:material_id>/", shell_edit_api),
    path("shell-material/delete/<int:shell_id>/", shell_delete_api),
    path("shell-material/bulk-delete/", bulk_delete_shell_materials_api),
]

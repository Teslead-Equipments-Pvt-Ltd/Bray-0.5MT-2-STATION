from django.urls import path
from bray_app.views.pages.employee_page_views import employee_list_page

urlpatterns = [
    path("employee/", employee_list_page, name="employee"),
]

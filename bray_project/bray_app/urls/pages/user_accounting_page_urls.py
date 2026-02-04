from django.urls import path
from bray_app.views.pages.user_accounting_page_views import user_accounting_page

urlpatterns = [
    path("user_accounting/", user_accounting_page, name="user_accounting"),
]

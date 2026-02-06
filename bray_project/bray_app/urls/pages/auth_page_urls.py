from django.urls import path
from bray_app.views.pages.auth_page_views import login_page, dashboard, change_password, logout_view

urlpatterns = [
    path('login/', login_page, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('change-password/', change_password, name='change_password'),
    path('logout/', logout_view, name='logout'),
]

"""
ABRS Page URL Configuration
"""
from django.urls import path
from bray_app.views.pages.abrs_page_views import abrs_page

urlpatterns = [
    path('abrs/', abrs_page, name='abrs'),
]

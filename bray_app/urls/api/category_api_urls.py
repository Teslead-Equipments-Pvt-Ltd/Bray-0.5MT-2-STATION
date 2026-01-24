from django.urls import path
from bray_app.views.api.category_api_views import api_category_update
 
urlpatterns = [
    
    path('category/', api_category_update, name='category_update'),

]
 


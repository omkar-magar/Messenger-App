from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('chatApp/admin/', admin.site.urls),  
    path('', include('chatApp.urls')),# <-- Make sure the first string here is empty!
    path('Django_Setup/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('Django_Setup/', include('django.contrib.auth.urls')),
]

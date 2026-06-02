from django.urls import path
from . import views
from . import api_views
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'chatApp'

urlpatterns = [
    # Web URLs (HTML)
    path('', views.room_list, name='room_list'),
    path('create/', views.create_room, name='room_create'),
    path('room/<str:room_name>/', views.room_detail, name='room_detail'),
    
    # API URLs (JSON for PySide6 App)
    path('api/register/', api_views.UserRegistrationAPIView.as_view(), name='api_register'),
    path('api/rooms/', api_views.RoomListAPIView.as_view(), name='api_room_list'),
    path('api/rooms/<str:room_name>/join/', api_views.RoomJoinAPIView.as_view(), name='api_room_join'),
    path('api/rooms/<str:room_name>/messages/', api_views.MessageListAPIView.as_view(), name='api_message_list'),
    path('api/token-auth/', obtain_auth_token, name='api_token_auth'),
]

from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer, UserRegistrationSerializer

class UserRegistrationAPIView(generics.CreateAPIView):
    """Endpoint for new users to register an account."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

class MessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class RoomListAPIView(generics.ListAPIView):
    """Returns a list of all chat rooms in JSON format."""
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

class RoomJoinAPIView(APIView):
    """Handles the 'Gatekeeper' logic for the API. Desktop apps POST here to join."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_name):
        room = get_object_or_404(Room, name=room_name)
        
        if request.user in room.participants.all():
            return Response({"message": "You are already a participant."})
            
        if room.is_private:
            password = request.data.get("password")
            if not password or not room.check_password(password):
                return Response({"error": "Incorrect or missing password."}, status=status.HTTP_403_FORBIDDEN)
        
        room.participants.add(request.user)
        return Response({"message": f"Successfully joined {room.name}."})

class MessageListAPIView(generics.ListAPIView):
    """Returns the chat history for a specific room, ONLY if the user is a participant."""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        room = get_object_or_404(Room, name=self.kwargs['room_name'])
        if self.request.user not in room.participants.all():
            raise PermissionDenied("You must join this room to view messages.")
        return Message.objects.filter(room=room)

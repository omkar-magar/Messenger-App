from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Room, Message

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserRegistrationSerializer(serializers.ModelSerializer):
    # write_only=True ensures the password is never returned in the API response
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email']

    def create(self, validated_data):
        # create_user securely hashes the password before saving
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class MessageSerializer(serializers.ModelSerializer):
    # This nests the UserSerializer so we get {"id": 1, "username": "omkar"} instead of just 1
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'content', 'timestamp']

class RoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        # We purposely exclude 'password' so it is never exposed in the JSON response
        fields = ['id', 'name', 'is_private', 'created_at', 'participants']
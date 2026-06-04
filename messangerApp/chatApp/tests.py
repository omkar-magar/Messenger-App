from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Room, Message

# Create your tests here.


class ChatModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")
        self.room = Room.objects.create(name="Test Room")
        self.room.participants.add(self.user1, self.user2)

    def test_room_creation(self):
        self.assertEqual(self.room.name, "Test Room")
        self.assertEqual(self.room.participants.count(), 2)
        self.assertIn(self.user1, self.room.participants.all())

    def test_message_creation(self):
        message = Message.objects.create(
            room=self.room, sender=self.user1, content="Hello, world!"
        )
        self.assertEqual(message.sender.username, "user1")
        self.assertEqual(message.content, "Hello, world!")
        self.assertEqual(self.room.messages.count(), 1)
        self.assertEqual(str(message), "user1: Hello, world!")


class ChatViewTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")
        
        self.public_room = Room.objects.create(name="PublicRoom")
        
        self.private_room = Room.objects.create(name="PrivateRoom", is_private=True)
        self.private_room.set_password("secret")
        self.private_room.save()

    def test_room_list_view(self):
        self.client.login(username="user1", password="password123")
        response = self.client.get(reverse('chatApp:room_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'room_list.html')
        self.assertContains(response, "PublicRoom")

    def test_public_room_auto_join(self):
        self.client.login(username="user1", password="password123")
        self.assertNotIn(self.user1, self.public_room.participants.all())
        
        response = self.client.get(reverse('chatApp:room_detail', kwargs={'room_name': self.public_room.name}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'room_detail.html')
        # Check if user was automatically added as a participant
        self.assertIn(self.user1, self.public_room.participants.all())

    def test_private_room_prompt_password(self):
        self.client.login(username="user1", password="password123")
        response = self.client.get(reverse('chatApp:room_detail', kwargs={'room_name': self.private_room.name}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'room_join.html')

    def test_private_room_wrong_password(self):
        self.client.login(username="user1", password="password123")
        response = self.client.post(
            reverse('chatApp:room_detail', kwargs={'room_name': self.private_room.name}),
            {"join_password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'room_join.html')
        self.assertEqual(response.context['error'], "Incorrect password")
        self.assertNotIn(self.user1, self.private_room.participants.all())

    def test_private_room_correct_password(self):
        self.client.login(username="user1", password="password123")
        response = self.client.post(
            reverse('chatApp:room_detail', kwargs={'room_name': self.private_room.name}),
            {"join_password": "secret"}
        )
        # Should add user and redirect back to the room detail view
        self.assertRedirects(response, reverse('chatApp:room_detail', kwargs={'room_name': self.private_room.name}))
        self.assertIn(self.user1, self.private_room.participants.all())

    def test_private_room_creation_requires_password(self):
        self.client.login(username="user1", password="password123")
        response = self.client.post(
            reverse('chatApp:room_create'),
            {"name": "SecretRoom", "is_private": "on", "password": ""}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'room_create.html')
        self.assertContains(response, "Private rooms require a password.")
        self.assertFalse(Room.objects.filter(name="SecretRoom").exists())

    def test_post_message(self):
        self.client.login(username="user1", password="password123")
        self.public_room.participants.add(self.user1)
        response = self.client.post(
            reverse('chatApp:room_detail', kwargs={'room_name': self.public_room.name}),
            {"content": "Hello from user1"}
        )
        # Should redirect back to the same page after posting
        self.assertRedirects(response, reverse('chatApp:room_detail', kwargs={'room_name': self.public_room.name}))
        self.assertEqual(Message.objects.filter(room=self.public_room).count(), 1)
        self.assertEqual(Message.objects.first().content, "Hello from user1")

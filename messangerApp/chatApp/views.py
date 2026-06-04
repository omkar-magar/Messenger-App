from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Room, Message

# Create your views here.

@login_required
def room_list(request):
    rooms = Room.objects.all()
    return render(request, "room_list.html", {"rooms": rooms})

@login_required
def room_detail(request, room_name):
    room = get_object_or_404(Room, name=room_name)

    if request.method == "POST":
        if "join_password" in request.POST:
            password = request.POST.get("join_password")
            if room.check_password(password):
                room.participants.add(request.user)
                return redirect('chatApp:room_detail', room_name=room.name)
            return render(request, "room_join.html", {"room": room, "error": "Incorrect password"})

        if request.user not in room.participants.all():
            if room.is_private:
                return render(request, "room_join.html", {"room": room, "error": "You must join the room before sending messages."})
            room.participants.add(request.user)

        content = request.POST.get("content", "").strip()
        if content:
            Message.objects.create(room=room, sender=request.user, content=content)
        return redirect('chatApp:room_detail', room_name=room.name)

    if request.user not in room.participants.all():
        if room.is_private:
            return render(request, "room_join.html", {"room": room})
        room.participants.add(request.user)

    messages = room.messages.all()
    return render(request, "room_detail.html", {"room": room, "messages": messages})

@login_required
def create_room(request):
    if request.method == "POST":
        name = request.POST.get("name")
        is_private = request.POST.get("is_private") == "on"
        password = request.POST.get("password") if is_private else None

        if not name:
            return render(request, "room_create.html", {"error": "Room name is required."})

        if is_private and not password:
            return render(request, "room_create.html", {"error": "Private rooms require a password."})

        if Room.objects.filter(name=name).exists():
            error_msg = "A room with this name already exists. Please choose another."
            return render(request, "room_create.html", {"error": error_msg})

        room = Room.objects.create(name=name, is_private=is_private)
        if is_private:
            room.set_password(password)
            room.save()
        room.participants.add(request.user)
        return redirect('chatApp:room_detail', room_name=room.name)

    return render(request, "room_create.html")
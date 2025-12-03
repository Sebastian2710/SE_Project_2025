from django.shortcuts import render
from .models import Message

def hello(request):
    message = Message.objects.first()
    return render(request, 'core/hello.html', {'message': message})

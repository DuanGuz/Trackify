# core/utils_messages.py
from django.contrib import messages

def clear_messages(request):
    """
    Consume/borra cualquier mensaje pendiente en la sesión.
    """
    storage = messages.get_messages(request)
    # Iterar consume los mensajes
    for _ in storage:
        pass
    # Por si acaso:
    storage.used = True

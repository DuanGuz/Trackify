from .models import *

def notifications_context(request):
    if not request.user.is_authenticated:
        return {"notif_unread_count": 0}
    count = Notificacion.objects.filter(usuario=request.user, is_read=False).count()
    return {"notif_unread_count": count}
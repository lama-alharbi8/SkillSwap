# skills/context_processors.py
from .models import Notification

def notifications_context(request):
    """
    Add notification data to all templates
    """
    if request.user.is_authenticated:
        try:
            # Count unread notifications
            unread_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            
            # Get 5 most recent notifications
            recent_notifications = Notification.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]
            
        except Exception as e:
            # If something goes wrong (model doesn't exist yet, etc.)
            unread_count = 0
            recent_notifications = []
    else:
        unread_count = 0
        recent_notifications = []
    
    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
    }
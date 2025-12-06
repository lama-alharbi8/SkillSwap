from .models import Notification

def notifications_context(request):
    """
    Add notification data to all templates
    """
    if request.user.is_authenticated:
        try:
         
            unread_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            

            recent_notifications = Notification.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]
            
        except Exception as e:
           
            unread_count = 0
            recent_notifications = []
    else:
        unread_count = 0
        recent_notifications = []
    
    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
    }
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Notification, SkillExchange

def create_notification(user, notification_type, title, message, content_object=None):

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        content_object=content_object,
    )
    return notification

def send_exchange_notification(exchange, notification_type, to_user=None):

    

    if to_user:
        recipients = [to_user]
    else:

        if exchange.initiator and exchange.responder:

            if notification_type == 'exchange_proposed':
                recipients = [exchange.responder]

            elif notification_type == 'exchange_accepted':
                recipients = [exchange.initiator]

            elif notification_type == 'exchange_completed':
                recipients = [exchange.initiator, exchange.responder]

            else:
                recipients = [exchange.get_other_party(exchange.initiator)]
        else:
            return [] 
    
    notification_data = {
        'exchange_proposed': {
            'title': 'New Exchange Proposal',
            'message': f'{exchange.initiator.username} has proposed an exchange with you!',
        },
        'exchange_accepted': {
            'title': 'Exchange Accepted',
            'message': f'{exchange.responder.username} has accepted your exchange proposal!',
        },
        'exchange_rejected': {
            'title': 'Exchange Rejected',
            'message': f'{exchange.responder.username} has declined your exchange proposal.',
        },
        'exchange_cancelled': {
            'title': 'Exchange Cancelled',
            'message': f'Exchange #{exchange.id} has been cancelled.',
        },
        'exchange_completed': {
            'title': 'Exchange Completed',
            'message': f'Your exchange with {exchange.get_other_party(exchange.initiator).username} has been completed!',
        },
        'rating_received': {
            'title': 'New Rating Received',
            'message': f'You received a rating from {exchange.get_other_party(exchange.initiator).username}!',
        },
    }
    
    notifications = []
    for user in recipients:
        data = notification_data.get(notification_type, {
            'title': 'Notification',
            'message': 'You have a new notification.',
        })
        
        notification = create_notification(
            user=user,
            notification_type=notification_type,
            title=data['title'],
            message=data['message'],
            content_object=exchange,
        )
        notifications.append(notification)
    
    return notifications

def get_unread_notifications_count(user):
    """Get count of unread notifications for a user"""
    return Notification.objects.filter(user=user, is_read=False).count()

def get_recent_notifications(user, limit=10):
    """Get recent notifications for a user"""
    return Notification.objects.filter(user=user).order_by('-created_at')[:limit]

def mark_all_as_read(user):
    """Mark all notifications as read for a user"""
    Notification.objects.filter(user=user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
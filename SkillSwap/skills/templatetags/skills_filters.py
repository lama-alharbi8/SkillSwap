from django import template

register = template.Library()

@register.filter
def get_status_bg(status):
    """Return Bootstrap background class based on status"""
    status_colors = {
        'pending': 'warning',
        'under_review': 'info',
        'negotiating': 'primary',
        'accepted': 'success',
        'in_progress': 'primary',
        'completed': 'dark',
        'cancelled': 'secondary',
        'disputed': 'danger',
    }
    return status_colors.get(status, 'secondary')

@register.filter
def get_score_color(score):
    """Return color based on fairness score"""
    if score >= 90:
        return 'success'
    elif score >= 70:
        return 'warning'
    else:
        return 'danger'

@register.filter
def notification_icon(notification_type):
    """Return icon class based on notification type"""
    icons = {
        'exchange_proposed': 'arrow-left-right',
        'exchange_accepted': 'hand-thumbs-up',
        'exchange_rejected': 'x-circle',
        'exchange_completed': 'check-circle',
        'exchange_cancelled': 'x-circle',
        'rating_received': 'star',
        'message': 'envelope',
        'system': 'info-circle',
    }
    return icons.get(notification_type, 'bell')
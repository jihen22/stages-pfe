from .models import Notification


def notifications(request):
    """Expose the unread count and the latest notifications to every template.

    Used by the shared top bar (bell) and the sidebar badge. Anonymous users
    get an empty context.
    """
    if not request.user.is_authenticated:
        return {}
    queryset = Notification.objects.filter(user=request.user)
    return {
        'unread_notifications_count': queryset.filter(is_read=False).count(),
        'recent_notifications': list(queryset[:5]),
    }

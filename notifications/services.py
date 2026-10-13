from .models import Notification


def notify(user, message, link=None):
    """Create an in-app notification for ``user``.

    Returns the created ``Notification`` or ``None`` when there is no valid
    recipient, so callers can fire-and-forget without extra guards.
    """
    if user is None or not getattr(user, 'pk', None):
        return None
    return Notification.objects.create(user=user, message=message, link=link or '')

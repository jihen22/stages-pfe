from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notifications_list(request):
    """Full list of the current user's notifications (any role)."""
    notifications = request.user.notifications.all()
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def notification_read(request, pk):
    """Mark one of *my* notifications as read, then follow its link if any."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    if notification.link and notification.link.startswith('/'):
        return redirect(notification.link)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read(request):
    """Mark every notification of the current user as read."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'Toutes vos notifications ont été marquées comme lues.')
    return redirect('notifications:list')

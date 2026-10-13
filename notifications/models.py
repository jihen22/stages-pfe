from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A short in-app message addressed to a single user.

    ``link`` is an optional internal path (e.g. ``/candidatures/recues/``) the
    notification points to; clicking a notification marks it as read and, when
    a link is set, redirects the user to it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Destinataire',
    )
    message = models.CharField('Message', max_length=255)
    link = models.CharField('Lien', max_length=255, blank=True)
    is_read = models.BooleanField('Lue', default=False)
    created_at = models.DateTimeField('Créée le', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'notification'
        verbose_name_plural = 'notifications'

    def __str__(self):
        return f'{self.user} — {self.message[:50]}'

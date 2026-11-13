"""URL configuration for the Stages & PFE platform."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

admin.site.site_header = "Administration Stages & PFE"
admin.site.site_title = "Stages & PFE Admin"
admin.site.index_title = "Tableau de bord d'administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('offres/', include('offres.urls')),
    path('candidatures/', include('candidatures.urls')),
    path('pfe/', include('pfe.urls')),
    path('soutenances/', include('soutenances.urls')),
    path('notifications/', include('notifications.urls')),
]

# Serve uploaded media (CVs) in development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

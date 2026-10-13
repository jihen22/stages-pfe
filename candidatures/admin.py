from django.contrib import admin

from .models import Candidature


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'offre', 'status', 'date_candidature')
    list_filter = ('status', 'offre__type')
    search_fields = ('etudiant__username', 'etudiant__last_name', 'offre__titre')
    date_hierarchy = 'date_candidature'
    list_select_related = ('etudiant', 'offre')

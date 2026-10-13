from django.contrib import admin

from .models import Offre


@admin.register(Offre)
class OffreAdmin(admin.ModelAdmin):
    list_display = ('titre', 'encadrant_pro', 'type', 'status', 'date_creation')
    list_filter = ('status', 'type')
    search_fields = ('titre', 'description', 'competences')
    date_hierarchy = 'date_creation'
    readonly_fields = ('date_creation', 'date_publication')
    list_select_related = ('encadrant_pro',)

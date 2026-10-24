from django.contrib import admin

from .models import Livrable, ProjetPFE


class LivrableInline(admin.TabularInline):
    model = Livrable
    extra = 0
    fields = ('titre', 'fichier', 'status', 'commentaire_encadrant', 'date_depot')
    readonly_fields = ('date_depot',)


@admin.register(ProjetPFE)
class ProjetPFEAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'etudiant', 'encadrant_acad', 'offre', 'status', 'date_creation')
    list_filter = ('status', 'date_creation')
    search_fields = (
        'sujet',
        'description',
        'etudiant__username',
        'etudiant__first_name',
        'etudiant__last_name',
        'encadrant_acad__username',
        'encadrant_acad__first_name',
        'encadrant_acad__last_name',
    )
    inlines = [LivrableInline]


@admin.register(Livrable)
class LivrableAdmin(admin.ModelAdmin):
    list_display = ('titre', 'projet', 'status', 'date_depot')
    list_filter = ('status', 'date_depot')
    search_fields = (
        'titre',
        'commentaire',
        'commentaire_encadrant',
        'projet__sujet',
        'projet__etudiant__username',
        'projet__etudiant__first_name',
        'projet__etudiant__last_name',
    )

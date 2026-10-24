from django.contrib import admin

from .models import NoteSoutenance, Soutenance


class NoteSoutenanceInline(admin.TabularInline):
    model = NoteSoutenance
    extra = 0
    autocomplete_fields = ('jury_member',)


@admin.register(Soutenance)
class SoutenanceAdmin(admin.ModelAdmin):
    list_display = ('projet', 'date', 'salle', 'get_moyenne', 'date_creation')
    list_filter = ('date', 'salle')
    search_fields = (
        'projet__sujet',
        'salle',
        'projet__etudiant__username',
        'projet__etudiant__last_name',
    )
    filter_horizontal = ('jury',)
    inlines = [NoteSoutenanceInline]

    @admin.display(description='Moyenne (/20)')
    def get_moyenne(self, obj):
        moy = obj.moyenne
        return f'{moy:.2f}/20' if moy is not None else '-'


@admin.register(NoteSoutenance)
class NoteSoutenanceAdmin(admin.ModelAdmin):
    list_display = ('soutenance', 'jury_member', 'note', 'date_saisie')
    list_filter = ('date_saisie', 'jury_member')
    search_fields = (
        'soutenance__projet__sujet',
        'jury_member__username',
        'jury_member__first_name',
        'jury_member__last_name',
        'remarque',
    )

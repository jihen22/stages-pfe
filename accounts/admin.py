from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ProfilEtudiant, ProfilEncadrantPro, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'role', 'domaine', 'is_staff')
    list_filter = ('role', 'domaine', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Rôle', {'fields': ('role', 'domaine')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Rôle', {'fields': ('role', 'domaine')}),
    )


@admin.register(ProfilEtudiant)
class ProfilEtudiantAdmin(admin.ModelAdmin):
    list_display = ('user', 'filiere', 'niveau', 'telephone')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'filiere')


@admin.register(ProfilEncadrantPro)
class ProfilEncadrantProAdmin(admin.ModelAdmin):
    list_display = ('user', 'entreprise', 'poste', 'telephone')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'entreprise')

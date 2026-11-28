from django.urls import path

from . import views

app_name = 'soutenances'

urlpatterns = [
    path('ma-soutenance/', views.ma_soutenance, name='ma_soutenance'),
    path('mes-soutenances/', views.mes_soutenances, name='mes_soutenances'),
    path('<int:pk>/convocation/', views.convocation, name='convocation'),
    path('<int:pk>/dossier/', views.dossier, name='dossier'),
    path('notes/', views.saisir_notes_list, name='saisir_notes'),
    path('notes/<int:pk>/', views.saisir_notes, name='saisir_note'),
    path('planning/', views.planning, name='planning'),
    path('planifier/', views.planifier_soutenance, name='planifier'),
    path('salles-creneaux/', views.ressources, name='ressources'),
    path('conflits/', views.conflits, name='conflits'),
    path('<int:pk>/modifier/', views.modifier_soutenance, name='modifier'),
    path('<int:pk>/deplacer/', views.deplacer_soutenance, name='deplacer'),
    path('salles/<int:pk>/basculer/', views.basculer_salle, name='basculer_salle'),
    path('creneaux/<int:pk>/supprimer/', views.supprimer_creneau, name='supprimer_creneau'),
]

from django.urls import path

from . import views

app_name = 'soutenances'

urlpatterns = [
    path('ma-soutenance/', views.ma_soutenance, name='ma_soutenance'),
    path('mes-soutenances/', views.mes_soutenances, name='mes_soutenances'),
    path('notes/', views.saisir_notes_list, name='saisir_notes'),
    path('notes/<int:pk>/', views.saisir_notes, name='saisir_note'),
    path('planning/', views.planning, name='planning'),
    path('planifier/', views.planifier_soutenance, name='planifier'),
]

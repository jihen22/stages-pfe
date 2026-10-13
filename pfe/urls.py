from django.urls import path

from . import views

app_name = 'pfe'

urlpatterns = [
    path('mon-pfe/', views.mon_pfe, name='mon_pfe'),
    path('mes-etudiants/', views.mes_etudiants, name='mes_etudiants'),
    path('livrables/', views.livrables_a_valider, name='livrables_a_valider'),
    path('affectations/', views.affectations, name='affectations'),
]

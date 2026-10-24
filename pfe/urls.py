from django.urls import path

from . import views

app_name = 'pfe'

urlpatterns = [
    path('mon-pfe/', views.mon_pfe, name='mon_pfe'),
    path('<int:projet_pk>/deposer/', views.deposer_livrable, name='deposer_livrable'),
    path('mes-etudiants/', views.mes_etudiants, name='mes_etudiants'),
    path('livrables/', views.livrables_a_valider, name='livrables_a_valider'),
    path('livrables/<int:pk>/valider/', views.valider_livrable, name='valider_livrable'),
    path('livrables/<int:pk>/corriger/', views.corriger_livrable, name='corriger_livrable'),
    path('affectations/', views.affectations, name='affectations'),
    path('affectations/<int:pk>/', views.affecter_encadrant, name='affecter_encadrant'),
]

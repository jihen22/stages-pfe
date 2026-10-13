from django.urls import path

from . import views

app_name = 'offres'

urlpatterns = [
    # Students
    path('', views.OffreListView.as_view(), name='offre_list'),

    # Company supervisors
    path('mes-offres/', views.MesOffresListView.as_view(), name='mes_offres'),
    path('nouvelle/', views.OffreCreateView.as_view(), name='offre_create'),

    # Administration
    path('a-valider/', views.OffresAValiderListView.as_view(), name='offres_a_valider'),

    # Item routes (keep after the static ones)
    path('<int:pk>/', views.OffreDetailView.as_view(), name='offre_detail'),
    path('<int:pk>/modifier/', views.OffreUpdateView.as_view(), name='offre_update'),
    path('<int:pk>/soumettre/', views.soumettre_offre, name='offre_soumettre'),
    path('<int:pk>/valider/', views.valider_offre, name='offre_valider'),
    path('<int:pk>/refuser/', views.refuser_offre, name='offre_refuser'),
]

from django.urls import path

from . import views

app_name = 'candidatures'

urlpatterns = [
    path('mes-candidatures/', views.MesCandidaturesListView.as_view(), name='mes_candidatures'),
    path('recues/', views.CandidaturesRecuesListView.as_view(), name='candidatures_recues'),
    path('offre/<int:offre_pk>/postuler/', views.postuler, name='postuler'),
    path('<int:pk>/accepter/', views.accepter_candidature, name='accepter'),
    path('<int:pk>/refuser/', views.refuser_candidature, name='refuser'),
]

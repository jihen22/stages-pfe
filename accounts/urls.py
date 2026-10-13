from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),

    # Redirects to the right dashboard depending on the role
    path('dashboard/', views.dashboard, name='dashboard'),

    # Profile & appearance
    path('profil/', views.preferences, name='preferences'),
    path('profil-etudiant/', views.profil_etudiant, name='profil_etudiant'),
    path('theme/', views.set_theme, name='set_theme'),

    # One dashboard per role
    path('dashboard/etudiant/', views.dashboard_etudiant, name='dashboard_etudiant'),
    path('dashboard/encadrant-pro/', views.dashboard_encadrant_pro, name='dashboard_encadrant_pro'),
    path('dashboard/encadrant-acad/', views.dashboard_encadrant_acad, name='dashboard_encadrant_acad'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/jury/', views.dashboard_jury, name='dashboard_jury'),
]

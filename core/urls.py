# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dashboard es la home
    # Login personalizado
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('buscador/', views.buscador, name='buscador'),
    path('entrenamiento/', views.entrenamiento, name='entrenamiento'),
    path('datos-brutos/', views.datos_brutos, name='datos_brutos'),
    path('examen/', views.examen, name='examen'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('cambiar-farmacia/', views.cambiar_farmacia, name='cambiar_farmacia'),
    path('importar/', views.importar, name='importar'),
]
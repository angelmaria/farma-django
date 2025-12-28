# efp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='efp_dashboard'),
    path('entrenamiento/', views.entrenamiento, name='efp_entrenamiento'),
    path('examen/', views.examen, name='efp_examen'),
    path('set_preferencia/', views.set_preferencia_efp, name='set_preferencia_efp'),
    # Crea estas vistas aunque sean copias básicas de las de core por ahora
    path('buscador/', views.buscador, name='efp_buscador'),
    path('datos-brutos/', views.datos_brutos, name='efp_datos_brutos'),
    path('configuracion/', views.configuracion, name='efp_configuracion'),
]
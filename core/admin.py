# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Oportunidad, Preferencia, PerfilFarmacia # Asegúrate de importar PerfilFarmacia

# 1. Definimos el perfil en línea (para que salga dentro de la ficha de usuario)
class PerfilInline(admin.StackedInline):
    model = PerfilFarmacia
    can_delete = False
    verbose_name_plural = 'Perfil de Farmacia'

# 2. Extendemos el Admin de Usuario original
class UserAdmin(BaseUserAdmin):
    inlines = (PerfilInline,)

# 3. Re-registramos el User con nuestra configuración
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Registramos tus otros modelos también para verlos
admin.site.register(Oportunidad)
admin.site.register(Preferencia)
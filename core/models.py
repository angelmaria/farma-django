# core/models.py
from django.contrib.auth.models import User
from django.db import models
from .mixins import CompetidoresStatsMixin

class PerfilFarmacia(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    farmacia_id = models.CharField(max_length=50, help_text="ID interno (ej: HF280050001)")
    
    def __str__(self):
        return f"{self.user.username} - {self.farmacia_id}"

class Oportunidad(CompetidoresStatsMixin, models.Model):
    """Modelo para oportunidades de Agrupaciones Homogéneas (medicamentos financiados)."""
    
    grupo_homogeneo = models.CharField(max_length=255)
    producto_recomendado = models.CharField(max_length=255)
    pvp_medio = models.DecimalField(max_digits=10, decimal_places=2)
    puc_medio = models.DecimalField(max_digits=10, decimal_places=2)
    margen_pct = models.DecimalField(max_digits=5, decimal_places=2)
    penetracion_pct = models.DecimalField(max_digits=5, decimal_places=2)
    a_sustituir = models.TextField() 
    ahorro_potencial = models.DecimalField(max_digits=10, decimal_places=2)
    codigo_nacional = models.CharField(max_length=20, blank=True, null=True, help_text="CN del producto recomendado")
    farmacia_id = models.CharField(max_length=50, default='HF280050001')

    class Meta:
        ordering = ['-ahorro_potencial']
        indexes = [
            models.Index(fields=['farmacia_id', 'ahorro_potencial']),
        ]

    def __str__(self):
        return self.grupo_homogeneo

class Preferencia(models.Model):
    """Preferencias manuales de laboratorio por grupo homogéneo."""
    
    grupo_homogeneo = models.CharField(max_length=255)
    laboratorio_preferente = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    farmacia_id = models.CharField(max_length=50, default='HF280050001')

    class Meta:
        unique_together = ('grupo_homogeneo', 'farmacia_id')
        indexes = [
            models.Index(fields=['farmacia_id', 'activo']),
        ]

    def __str__(self):
        return f"{self.grupo_homogeneo} -> {self.laboratorio_preferente}"
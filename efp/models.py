# efp/models.py
from django.db import models
from core.mixins import CompetidoresStatsMixin

class OportunidadEFP(CompetidoresStatsMixin, models.Model):
    """Modelo para oportunidades de EFP (Especialidades Farmacéuticas Publicitarias - Venta Libre)."""
    
    farmacia_id = models.CharField(max_length=50, db_index=True)
    
    # Identificación Databricks
    id_agrupacion = models.IntegerField() 
    nombre_grupo = models.CharField(max_length=255) # El nombre del síntoma/grupo
    
    # Jerarquía (Viene de tu JSON local)
    familia = models.CharField(max_length=100, default="Otras")      # Ej: RESPIRATORIO
    subfamilia = models.CharField(max_length=100, default="General") # Ej: TOS
    
    # El Campeón
    producto_recomendado = models.CharField(max_length=255)
    
    # Económicos
    pvp_medio = models.DecimalField(max_digits=8, decimal_places=2)
    margen_pct = models.DecimalField(max_digits=5, decimal_places=2)
    ahorro_potencial = models.DecimalField(max_digits=10, decimal_places=2)

    codigo_nacional = models.CharField(max_length=20, default="", blank=True)
    
    # Competidores (String parseable)
    a_sustituir = models.TextField(blank=True)

    class Meta:
        ordering = ['-ahorro_potencial']
        unique_together = ('farmacia_id', 'id_agrupacion')
        indexes = [
            models.Index(fields=['farmacia_id', 'familia']),
        ]

    def __str__(self):
        return f"{self.familia} > {self.nombre_grupo}"

class PreferenciaEFP(models.Model):
    farmacia_id = models.CharField(max_length=50, db_index=True)
    id_agrupacion = models.IntegerField()
    producto_preferido = models.CharField(max_length=255)
    
    class Meta:
        unique_together = ('farmacia_id', 'id_agrupacion')
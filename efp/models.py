# efp/models.py
from django.db import models
import re

class OportunidadEFP(models.Model):
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

    # Añadimos este campo clave:
    codigo_nacional = models.CharField(max_length=20, default="", blank=True)
    
    # Competidores (String parseable)
    a_sustituir = models.TextField(blank=True)

    class Meta:
        ordering = ['-ahorro_potencial']
        unique_together = ('farmacia_id', 'id_agrupacion')

    def __str__(self):
        return f"{self.familia} > {self.nombre_grupo}"

    def get_competidores_stats(self):
        stats = []
        
        # 1. CAMPEÓN
        try:
            m_campeon = float(self.margen_pct) if self.margen_pct else 0.0
        except: m_campeon = 0.0

        stats.append({
            'nombre': self.producto_recomendado, 
            'unidades': 0, 
            'margen': m_campeon, 
            'penet': 0, 
            'es_campeon': True,
            'cn': self.codigo_nacional # CN del campeón
        })

        if not self.a_sustituir: 
            return stats

        # 2. COMPETENCIA
        raw_string = str(self.a_sustituir).replace('\r', '').replace('\n', '')
        items = raw_string.split(' || ')
        
        for item in items:
            item = item.strip()
            if not item: continue

            # "NOMBRE (UNIDADES###MARGEN###CUOTA###CN)"
            nombre_part, separador, datos_part = item.rpartition(' (')
            
            if not separador: continue 

            datos_limpios = datos_part.rstrip(')')
            parts = datos_limpios.split('###')
            
            # Ahora esperamos 5 partes: Unidades###Margen###Cuota###CN###PVP
            if len(parts) >= 3:
                try:
                    u = int(float(parts[0]))
                    m = float(parts[1])
                    p = float(parts[2])
                    
                    cn_comp = parts[3] if len(parts) > 3 else ""
                    pvp_comp = float(parts[4]) if len(parts) > 4 else 0.0 # Capture PVP
                    
                    stats.append({
                        'nombre': nombre_part.strip(),
                        'unidades': u,
                        'margen': m,
                        'penet': p,
                        'cn': cn_comp,
                        'pvp': pvp_comp, # Add to dict
                        'es_campeon': False
                    })
                except:
                    continue

        return sorted(stats, key=lambda x: x['margen'], reverse=True)

class PreferenciaEFP(models.Model):
    farmacia_id = models.CharField(max_length=50, db_index=True)
    id_agrupacion = models.IntegerField()
    producto_preferido = models.CharField(max_length=255)
    
    class Meta:
        unique_together = ('farmacia_id', 'id_agrupacion')
# core/models.py
from django.contrib.auth.models import User
from django.db import models
import re

class PerfilFarmacia(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    farmacia_id = models.CharField(max_length=50, help_text="ID interno (ej: HF280050001)")
    
    def __str__(self):
        return f"{self.user.username} - {self.farmacia_id}"

class Oportunidad(models.Model):
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

    def __str__(self):
        return self.grupo_homogeneo

    def get_competidores_stats(self):
        """
        Parsea el string 'Marca (Unidades) || Marca2 (Unidades)'
        y devuelve una lista de diccionarios con % calculado.
        """
        items = self.a_sustituir.split(' || ')
        stats = []
        total_competencia = 0
        parsed_items = []

        # Regex actualizado para capturar (Unidades | Margen | CN)
        # Soporta el formato antiguo por seguridad
        regex_nuevo = r'\((\d+)\|(\d+)%\|(\d+)\)$'
        regex_viejo = r'\((\d+)\|(\d+)%\)$'

        for item in items:
            match_new = re.search(regex_nuevo, item)
            match_old = re.search(regex_viejo, item)
            
            if match_new:
                unidades = int(match_new.group(1))
                margen = int(match_new.group(2))
                cn = match_new.group(3)
                nombre = item.split('(')[0].strip()
                parsed_items.append({'nombre': nombre, 'unidades': unidades, 'margen': margen, 'cn': cn})
                total_competencia += unidades
            elif match_old:
                unidades = int(match_old.group(1))
                margen = int(match_old.group(2))
                nombre = item.split('(')[0].strip()
                parsed_items.append({'nombre': nombre, 'unidades': unidades, 'margen': margen, 'cn': ''})
                total_competencia += unidades

        # 2. Calcular unidades de NUESTRO producto
        if self.penetracion_pct < 100:
            denom = (1 - (float(self.penetracion_pct)/100))
            if denom == 0: denom = 0.0001
            total_mercado = total_competencia / denom
            nuestras_unidades = total_mercado - total_competencia
        else:
            nuestras_unidades = total_competencia 
            
        total_mercado_real = total_competencia + nuestras_unidades

        # Formateo final
        if total_mercado_real > 0:
            # --- CAMPEÓN ---
            raw_penet_campeon = (nuestras_unidades / total_mercado_real) * 100
            
            stats.append({
                'nombre': self.producto_recomendado, # Sin icono de copa aquí
                'penet': f"{raw_penet_campeon:.2f}",
                'margen': self.margen_pct,
                'es_campeon': True,
                'cn': self.codigo_nacional # Usamos el campo del modelo
            })
            
            # --- COMPETIDORES ---
            for p in parsed_items:
                raw_penet_comp = (p['unidades'] / total_mercado_real) * 100
                stats.append({
                    'nombre': p['nombre'],
                    'penet': f"{raw_penet_comp:.2f}",
                    'margen': p['margen'],
                    'es_campeon': False,
                    'cn': p['cn'] # CN extraído del string
                })
        return stats

class Preferencia(models.Model):
    grupo_homogeneo = models.CharField(max_length=255, unique=True)
    laboratorio_preferente = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.grupo_homogeneo} -> {self.laboratorio_preferente}"
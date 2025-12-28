# core/mixins.py
"""
Mixins compartidos para evitar duplicación de código entre apps.
"""
import re


class CompetidoresStatsMixin:
    """
    Mixin compartido para parsear estadísticas de competidores.
    
    Parsea el formato: 'Marca (Unidades|Margen%|CN) || Marca2 (...)'
    y devuelve una lista de diccionarios con estadísticas calculadas.
    
    Requiere que el modelo tenga los campos:
    - a_sustituir: TextField con el string de competidores
    - producto_recomendado: CharField con el producto recomendado
    - margen_pct: DecimalField con el margen porcentual
    - penetracion_pct: DecimalField (solo para Oportunidad de AH)
    - codigo_nacional: CharField con el CN del producto recomendado
    """
    
    def get_competidores_stats(self):
        """
        Parsea el campo a_sustituir y devuelve estadísticas calculadas.
        
        Returns:
            list: Lista de diccionarios con keys:
                - nombre: str, nombre del producto
                - unidades: int, unidades vendidas (si aplica)
                - margen: float, porcentaje de margen
                - penet: float, porcentaje de penetración
                - cn: str, código nacional
                - es_campeon: bool, True si es el producto recomendado
                - pvp: float, precio venta público (solo EFP)
        """
        if not hasattr(self, 'a_sustituir') or not self.a_sustituir:
            return []
        
        stats = []
        raw_string = str(self.a_sustituir).replace('\r', '').replace('\n', '')
        items = raw_string.split(' || ')
        
        # Para AH: calcular penetración basada en unidades
        if hasattr(self, 'penetracion_pct'):
            return self._parse_ah_format(items)
        else:
            # Para EFP: formato diferente
            return self._parse_efp_format(items)
    
    def _parse_ah_format(self, items):
        """Parsea formato de Agrupaciones Homogéneas."""
        stats = []
        total_competencia = 0
        parsed_items = []
        
        # Regex para (Unidades|Margen%|CN)
        regex_nuevo = r'\((\d+)\|(\d+)%\|(\d+)\)$'
        regex_viejo = r'\((\d+)\|(\d+)%\)$'
        
        for item in items:
            item = item.strip()
            if not item:
                continue
                
            match_new = re.search(regex_nuevo, item)
            match_old = re.search(regex_viejo, item)
            
            if match_new:
                unidades = int(match_new.group(1))
                margen = int(match_new.group(2))
                cn = match_new.group(3)
                nombre = item.split('(')[0].strip()
                parsed_items.append({
                    'nombre': nombre,
                    'unidades': unidades,
                    'margen': margen,
                    'cn': cn
                })
                total_competencia += unidades
            elif match_old:
                unidades = int(match_old.group(1))
                margen = int(match_old.group(2))
                nombre = item.split('(')[0].strip()
                parsed_items.append({
                    'nombre': nombre,
                    'unidades': unidades,
                    'margen': margen,
                    'cn': ''
                })
                total_competencia += unidades
        
        # Calcular unidades del campeón
        if hasattr(self, 'penetracion_pct') and self.penetracion_pct < 100:
            denom = 1 - (float(self.penetracion_pct) / 100)
            if denom > 0:
                total_mercado = total_competencia / denom
                nuestras_unidades = total_mercado - total_competencia
            else:
                nuestras_unidades = total_competencia
        else:
            nuestras_unidades = total_competencia
        
        total_mercado_real = total_competencia + nuestras_unidades
        
        # Agregar el campeón
        if total_mercado_real > 0:
            penet_campeon = (nuestras_unidades / total_mercado_real) * 100
            stats.append({
                'nombre': self.producto_recomendado,
                'penet': f"{penet_campeon:.2f}",
                'margen': float(self.margen_pct) if hasattr(self, 'margen_pct') else 0,
                'es_campeon': True,
                'cn': getattr(self, 'codigo_nacional', '')
            })
            
            # Agregar competidores
            for p in parsed_items:
                penet_comp = (p['unidades'] / total_mercado_real) * 100
                stats.append({
                    'nombre': p['nombre'],
                    'penet': f"{penet_comp:.2f}",
                    'margen': p['margen'],
                    'es_campeon': False,
                    'cn': p['cn']
                })
        
        return stats
    
    def _parse_efp_format(self, items):
        """Parsea formato de EFP (Venta Libre)."""
        stats = []
        
        # Agregar el campeón primero
        stats.append({
            'nombre': self.producto_recomendado,
            'unidades': 0,
            'margen': float(self.margen_pct) if hasattr(self, 'margen_pct') else 0,
            'penet': 0,
            'es_campeon': True,
            'cn': getattr(self, 'codigo_nacional', '')
        })
        
        # Parsear competidores: "NOMBRE (UNIDADES###MARGEN###CUOTA###CN###PVP)"
        for item in items:
            item = item.strip()
            if not item:
                continue
            
            nombre_part, separador, datos_part = item.rpartition(' (')
            if not separador:
                continue
            
            datos_limpios = datos_part.rstrip(')')
            parts = datos_limpios.split('###')
            
            if len(parts) >= 3:
                try:
                    unidades = int(float(parts[0]))
                    margen = float(parts[1])
                    penet = float(parts[2])
                    cn = parts[3] if len(parts) > 3 else ""
                    pvp = float(parts[4]) if len(parts) > 4 else 0.0
                    
                    stats.append({
                        'nombre': nombre_part.strip(),
                        'unidades': unidades,
                        'margen': margen,
                        'penet': penet,
                        'cn': cn,
                        'pvp': pvp,
                        'es_campeon': False
                    })
                except (ValueError, IndexError):
                    continue
        
        return sorted(stats, key=lambda x: x['margen'], reverse=True)

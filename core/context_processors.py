from .models import Oportunidad
import random

def contexto_global(request):
    """
    Este procesador de contexto inyecta variables globales en TODAS las plantillas.
    1. El Tip del día dinámico.
    2. La lista de farmacias disponibles para el selector.
    3. La farmacia activa actualmente.
    """
    
    # --- PARTE 1: FARMACIAS DISPONIBLES ---
    f_activa = request.session.get('farmacia_activa', 'HF280050001')
    
    # Buscamos todos los IDs únicos de farmacia que hay en la base de datos
    farmacias_disponibles = Oportunidad.objects.values_list('farmacia_id', flat=True).distinct().order_by('farmacia_id')
    
    # --- PARTE 2: TIP DEL DÍA ---
    # Buscamos una oportunidad de ahorro > 500€ en la farmacia activa
    oportunidad = Oportunidad.objects.filter(farmacia_id=f_activa, ahorro_potencial__gt=500).order_by('?').first()
    
    if oportunidad:
        competidor = "la marca"
        if oportunidad.a_sustituir:
            stats = oportunidad.get_competidores_stats()
            if stats:
                competidor = stats[0]['nombre'] # Cogemos el primer competidor
                
        mensaje = f"Sustituyendo <b>{competidor}</b> por <b>{oportunidad.producto_recomendado[:20]}...</b> aumentas el margen un <b>{oportunidad.margen_pct}%</b>."
    else:
        mensaje = "Revisa los márgenes de los genéricos, ¡cada céntimo cuenta!"
        
    # Devolvemos TODO junto
    return {
        'tip_del_dia': mensaje,
        'farmacias_disponibles': farmacias_disponibles,
        'farmacia_activa': f_activa
    }
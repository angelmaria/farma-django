# core/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from .models import Oportunidad, Preferencia
from efp.models import OportunidadEFP
from .forms import PreferenciaForm
from .services import sincronizar_desde_databricks
from efp.services import sincronizar_efp_desde_databricks
from core.services import sincronizar_desde_databricks, obtener_farmacias_cloud
import random

@login_required(login_url='login')
def dashboard(request):
    user = request.user
    farmacias_disponibles = []
    
    # --- 1. DETERMINAR QUÉ FARMACIA VER ---
    if user.is_superuser or user.is_staff:
        es_admin = True
        farmacias_disponibles, _ = obtener_farmacias_cloud()
        
        # Recuperar selección de sesión o usar la primera por defecto
        farmacia_activa = request.session.get('farmacia_activa')
        if not farmacia_activa and farmacias_disponibles:
            farmacia_activa = farmacias_disponibles[0]
            request.session['farmacia_activa'] = farmacia_activa
            
    else:
        es_admin = False
        try:
            farmacia_activa = user.perfil.farmacia_id
            farmacias_disponibles = [farmacia_activa]
        except:
            return render(request, 'core/error_config.html', {'msg': 'Usuario sin farmacia asignada'})

    # --- 2. OBTENER DATOS FILTRADOS ---
    # Usamos farmacia_activa para filtrar TODO
    oportunidades = Oportunidad.objects.filter(farmacia_id=farmacia_activa)
    efp_data = OportunidadEFP.objects.filter(farmacia_id=farmacia_activa)

    # --- 3. CÁLCULOS KPI (Fusionado de tu versión antigua) ---
    # Ahorro total (Suma de AH + EFP)
    ahorro_ah = oportunidades.aggregate(Sum('ahorro_potencial'))['ahorro_potencial__sum'] or 0
    ahorro_efp = efp_data.aggregate(Sum('ahorro_potencial'))['ahorro_potencial__sum'] or 0
    total_ahorro = ahorro_ah + ahorro_efp
    
    ahorro_mensual = total_ahorro / 12

    # Top 5 (Solo de AH por ahora, o puedes mezclar)
    top_5 = oportunidades.order_by('-ahorro_potencial')[:5]

    total_grupos = oportunidades.count() + efp_data.count()

    # Cálculo marcas a sustituir (AH)
    total_marcas = 0
    for op in oportunidades:
        if op.a_sustituir:
            total_marcas += len(op.a_sustituir.split(' || '))
            
    # Cálculo marcas a sustituir (EFP)
    for op in efp_data:
        if op.a_sustituir:
            total_marcas += len(op.a_sustituir.split(' || '))

    context = {
        'farmacia_activa': farmacia_activa,
        'es_admin': es_admin,
        'farmacias_disponibles': farmacias_disponibles,
        
        'top_5': top_5,
        'total_ahorro': total_ahorro,
        'ahorro_mensual': ahorro_mensual,
        'total_grupos': total_grupos,
        'total_marcas': total_marcas,
        'active_tab': 'dashboard',
        'segmento': 'AH',
    }
    
    return render(request, 'core/dashboard.html', context)

# --- VISTA PARA CAMBIAR DE FARMACIA (Solo Admins) ---
@staff_member_required
def cambiar_farmacia(request):
    if request.method == 'POST':
        nueva_farmacia = request.POST.get('farmacia_id')
        if nueva_farmacia:
            request.session['farmacia_activa'] = nueva_farmacia
    
    # Redirigimos a la página desde donde vino (o al dashboard por defecto)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# --- BUSCADOR ---
def buscador(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    query = request.GET.get('q', '')
    resultados = []
    
    if query:
        # Filtramos por Farmacia Y por coincidencia de texto
        resultados = Oportunidad.objects.filter(farmacia_id=f_id).filter(
            Q(a_sustituir__icontains=query) | 
            Q(grupo_homogeneo__icontains=query)
        )
    
    context = {
        'farmacia_activa': f_id,
        'query': query,
        'resultados': resultados,
        'active_tab': 'buscador',
        'segmento': 'AH',
    }
    return render(request, 'core/buscador.html', context)

# --- DATOS BRUTOS ---
def datos_brutos(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    
    # 1. Capturar parámetro de ordenación (Por defecto: Ahorro descendente)
    order_param = request.GET.get('order', '-ahorro_potencial')
    
    # 2. Lista blanca de campos permitidos (Seguridad)
    # Esto evita que alguien intente ordenar por campos que no existen y rompa la web
    campos_validos = [
        'grupo_homogeneo', '-grupo_homogeneo',
        'producto_recomendado', '-producto_recomendado',
        'pvp_medio', '-pvp_medio',
        'margen_pct', '-margen_pct',
        'ahorro_potencial', '-ahorro_potencial'
    ]
    
    # Si el parámetro no es válido, usamos el default
    orden_final = order_param if order_param in campos_validos else '-ahorro_potencial'

    # 3. Consultar y Ordenar
    datos = Oportunidad.objects.filter(farmacia_id=f_id).order_by(orden_final)
    
    context = {
        'farmacia_activa': f_id,
        'datos': datos,
        'active_tab': 'datos_brutos',
        'segmento': 'AH',
        'current_order': orden_final, # Pasamos el orden actual para pintar las flechas
    }
    return render(request, 'core/datos_brutos.html', context)

# --- ENTRENAMIENTO (Gimnasio) ---
def entrenamiento(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    
    # Filtramos pool de preguntas por farmacia
    items_qs = Oportunidad.objects.filter(farmacia_id=f_id)
    
    if not items_qs.exists():
        # Manejo de error si no hay datos para esa farmacia
        return render(request, 'core/entrenamiento.html', {'error': 'No hay datos cargados para esta farmacia', 'active_tab': 'entrenamiento'})

    item = items_qs.order_by('?').first()
    
    # Lógica de Preferencia filtrada por farmacia
    try:
        pref = Preferencia.objects.get(
            grupo_homogeneo=item.grupo_homogeneo, 
            farmacia_id=f_id,
            activo=True
        )
        producto_final = f"{pref.laboratorio_preferente} (Preferencia)"
        es_preferencia = True
    except Preferencia.DoesNotExist:
        producto_final = item.producto_recomendado
        es_preferencia = False

    # Extraer competidor "sucio"
    marca_ask = item.grupo_homogeneo
    if item.a_sustituir:
        competidores = item.get_competidores_stats()
        if competidores:
            # Buscamos alguno que NO sea campeón
            for c in competidores:
                if not c.get('es_campeon'):
                    marca_ask = c['nombre']
                    break

    # Objeto modificado para la vista (fake attributes para simplificar template)
    item.producto_visual = producto_final 
    
    context = {
        'farmacia_activa': f_id,
        'item': item,
        'marca_ask': marca_ask,
        'es_preferencia': es_preferencia,
        'active_tab': 'entrenamiento',
        'segmento': 'AH',
    }
    return render(request, 'core/entrenamiento.html', context)

# --- EXAMEN ---
@login_required(login_url='login')
def examen(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    MAX_PREGUNTAS = 10 

    # 1. Reset limpio
    if 'reset' in request.GET or 'aciertos' not in request.session:
        request.session['aciertos'] = 0
        request.session['total'] = 0
        if 'reset' in request.GET:
            return redirect('examen')

    mensaje = None
    es_correcto = None

    # 2. Procesar respuesta (POST)
    if request.method == 'POST':
        elegido = request.POST.get('opcion')
        correcto = request.POST.get('correcto')
        
        if elegido and correcto:
            request.session['total'] += 1 
            if elegido == correcto:
                request.session['aciertos'] += 1
                mensaje = "¡Correcto! Has elegido la opción más rentable del grupo."
                es_correcto = True
            else:
                mensaje = f"Incorrecto. Dentro de este grupo, la opción óptima es {correcto}"
                es_correcto = False

    # 3. Game Over
    if request.session['total'] >= MAX_PREGUNTAS and request.method == 'GET':
        score = (request.session['aciertos'] / MAX_PREGUNTAS) * 100
        # ... (Tu lógica de feedback igual que antes) ...
        if score == 100: feedback = "¡Increíble! Eres un maestro de la sustitución."
        elif score >= 50: feedback = "Bien, pero sigue practicando."
        else: feedback = "Necesitas repasar."
        
        context = {
            'finalizado': True,
            'aciertos': request.session['aciertos'],
            'total': MAX_PREGUNTAS,
            'score': score,
            'feedback': feedback,
            'active_tab': 'examen',
            'segmento': 'AH'
        }
        return render(request, 'core/examen.html', context)
    
    # 4. GENERAR NUEVA PREGUNTA (Lógica Mejorada)
    items_qs = Oportunidad.objects.filter(farmacia_id=f_id)
    
    # Intentamos buscar una pregunta válida (que tenga competencia)
    # Hacemos hasta 10 intentos para no bloquear el servidor si todo son monopolios
    item_valido = None
    distractores_reales = []
    respuesta_correcta = ""
    origen = ""

    for _ in range(10): 
        posible_item = items_qs.order_by('?').first()
        if not posible_item: break # No hay datos

        # Determinamos la respuesta correcta (Preferencia o Recomendado)
        try:
            pref = Preferencia.objects.get(
                grupo_homogeneo=posible_item.grupo_homogeneo,
                farmacia_id=f_id,
                activo=True
            )
            respuesta_correcta = pref.laboratorio_preferente
            origen = "Preferencia"
        except Preferencia.DoesNotExist:
            respuesta_correcta = posible_item.producto_recomendado
            origen = "Algoritmo"

        # BÚSQUEDA DE DISTRACTORES (Rivales del MISMO grupo)
        # Usamos el método que ya tienes programado en models.py
        competencia_stats = posible_item.get_competidores_stats()
        
        # Filtramos: Queremos nombres que NO sean la respuesta correcta
        # competencia_stats devuelve una lista de dicts: [{'nombre': 'Cinfa', ...}, ...]
        # Use set() to remove potential duplicates immediately
        posibles_rivales = list(set([
            c['nombre'] for c in competencia_stats 
            if c['nombre'].strip().upper() != respuesta_correcta.strip().upper()
        ]))

        # Si hay al menos 1 rival, la pregunta es válida (será A vs B)
        if posibles_rivales:
            item_valido = posible_item
            # Take up to 2 random rivals (if only 1 exists, take 1)
            num_distractores = min(len(posibles_rivales), 2)
            distractores_reales = random.sample(posibles_rivales, num_distractores)
            break
    
    # Si tras 10 intentos no encontramos nada (muy raro), mostramos error o fallback
    if not item_valido:
        return render(request, 'core/dashboard.html', {'active_tab': 'dashboard', 'segmento': 'AH'})

    # Montamos las opciones finales
    opciones = distractores_reales + [respuesta_correcta]
    random.shuffle(opciones)

    # Marca para el título (nombre del grupo homogéneo)
    marca_ask = item_valido.grupo_homogeneo

    context = {
        'farmacia_activa': f_id,
        'item': item_valido,
        'marca_ask': marca_ask,
        'opciones': opciones,
        'respuesta_correcta': respuesta_correcta,
        'mensaje': mensaje,
        'es_correcto': es_correcto,
        'aciertos': request.session['aciertos'],
        'total': request.session['total'],
        'origen': origen,
        'finalizado': False,
        'active_tab': 'examen',
        'segmento': 'AH'
    }
    return render(request, 'core/examen.html', context)

# --- CONFIGURACIÓN ---
def configuracion(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    
    # 1. Obtenemos datos
    oportunidades = Oportunidad.objects.filter(farmacia_id=f_id).order_by('grupo_homogeneo')
    
    # 2. Diccionario de preferencias existentes (filtrado por farmacia)
    preferencias_dict = {
        p.grupo_homogeneo: p 
        for p in Preferencia.objects.filter(farmacia_id=f_id, activo=True)
    }

    # 3. Guardado (POST)
    if request.method == 'POST':
        grupo = request.POST.get('grupo_hidden')
        producto_elegido = request.POST.get('producto_elegido') # Cambiamos nombre variable
        is_active = request.POST.get('activo') == 'on'
        
        if grupo and producto_elegido:
            Preferencia.objects.update_or_create(
                grupo_homogeneo=grupo,
                farmacia_id=f_id,
                defaults={'laboratorio_preferente': producto_elegido, 'activo': is_active}
            )
            return redirect('configuracion')

    lista_config = []
    
    for op in oportunidades:
        # A. Construir lista de opciones (Recomendado + Competencia)
        opciones_disponibles = []
        
        # 1. El Ganador actual (Opción por defecto del sistema)
        opciones_disponibles.append(op.producto_recomendado)
        
        # 2. Los competidores (Los extraemos de la cadena de texto)
        # Usamos el método helper que ya creamos en models.py
        competidores_stats = op.get_competidores_stats()
        for c in competidores_stats:
            # Evitamos duplicados si el recomendado sale en la lista
            if c['nombre'] not in opciones_disponibles: 
                opciones_disponibles.append(c['nombre'])
        
        # B. Determinar selección actual
        pref = preferencias_dict.get(op.grupo_homogeneo)
        
        if pref:
            valor_actual = pref.laboratorio_preferente
            es_manual = True
            activo = pref.activo
        else:
            valor_actual = op.producto_recomendado
            es_manual = False
            activo = True

        lista_config.append({
            'grupo': op.grupo_homogeneo,
            'valor_actual': valor_actual,
            'opciones': sorted(opciones_disponibles), # Ordenamos alfabéticamente
            'es_manual': es_manual,
            'activo': activo,
            'margen': op.margen_pct
        })

    context = {
        'lista_config': lista_config,
        'active_tab': 'configuracion',
        'segmento': 'AH',
    }
    return render(request, 'core/configuracion.html', context)

from .services import sincronizar_desde_databricks, obtener_farmacias_cloud # <--- Importar nuevo servicio

def importar(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')

    # --- OPTIMIZACIÓN: CACHÉ DE FARMACIAS ---
    # Solo conectamos a Databricks si no tenemos la lista en la sesión
    if 'lista_farmacias_cloud' in request.session:
        lista_farmacias_cloud = request.session['lista_farmacias_cloud']
        error_cloud = None
    else:
        # Si no está en caché, conectamos (tardará unos segundos)
        lista_farmacias_cloud, error_cloud = obtener_farmacias_cloud()
        if not error_cloud:
            request.session['lista_farmacias_cloud'] = lista_farmacias_cloud
    # ----------------------------------------
    
    mensaje = None
    tipo_mensaje = ""
    
    if error_cloud:
         mensaje = f"Error conectando a Databricks: {error_cloud}"
         tipo_mensaje = "warning"

    if request.method == 'POST':
        farmacia_input = request.POST.get('farmacia_input')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')

        if farmacia_input and fecha_inicio and fecha_fin:
            # 1. Sincronizar Medicamentos (Core)
            # Asegúrate de que esta función devuelve (int, str)
            num_ah, error_ah = sincronizar_desde_databricks(farmacia_input, fecha_inicio, fecha_fin)
            
            # 2. Sincronizar EFP (Nueva App)
            num_efp, error_efp = sincronizar_efp_desde_databricks(farmacia_input, fecha_inicio, fecha_fin)
            
            if error_ah or error_efp:
                # Mostramos error si falla CUALQUIERA de los dos
                err_msg = ""
                if error_ah: err_msg += f"AH: {error_ah}. "
                if error_efp: err_msg += f"EFP: {error_efp}."
                mensaje = f"Hubo errores: {err_msg}"
                tipo_mensaje = "danger"
            else:
                mensaje = f"¡Éxito! Datos actualizados: {num_ah} grupos AH y {num_efp} categorías EFP."
                tipo_mensaje = "success"

                # Guardamos datos en sesión
                request.session['farmacia_activa'] = farmacia_input
                request.session['fecha_inicio'] = fecha_inicio
                request.session['fecha_fin'] = fecha_fin
                
                # Actualizamos la variable local para que el selector muestre la nueva
                f_id = farmacia_input 
        else:
            mensaje = "Por favor completa todos los campos."
            tipo_mensaje = "warning"

    # IMPORTANTE: Siempre retornar el render al final
    context = {
        'farmacia_activa': f_id,
        'lista_farmacias': lista_farmacias_cloud,
        'mensaje': mensaje,
        'tipo_mensaje': tipo_mensaje,
        'active_tab': 'configuracion',
        'segmento': 'AH',
    }
    return render(request, 'core/importar.html', context)
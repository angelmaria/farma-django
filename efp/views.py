# efp/views.py
from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from .models import OportunidadEFP, PreferenciaEFP
from .services import ICONOS_FAMILIAS, generar_pregunta_examen
import random

# --- DASHBOARD ---
@login_required(login_url='login')
def dashboard(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    qs = OportunidadEFP.objects.filter(farmacia_id=f_id)
    
    # --- LOGICA DE PREFERENCIAS ---
    prefs = { p.id_agrupacion: p.producto_preferido for p in PreferenciaEFP.objects.filter(farmacia_id=f_id) }
    
    oportunidades_list = []
    for item in qs:
        if item.id_agrupacion in prefs:
            prod_pref = prefs[item.id_agrupacion]
            if item.producto_recomendado != prod_pref:
                stats = item.get_competidores_stats()
                match = next((s for s in stats if s['nombre'] == prod_pref), None)
                
                if match:
                    item.producto_recomendado = prod_pref
                    item.margen_pct = match['margen']
                    item.es_preferido = True 
        else:
            item.es_preferido = False
            
        oportunidades_list.append(item)
    
    # Filtros de Familia
    familias = sorted(list(set(o.familia for o in oportunidades_list)))
    familia_activa = request.GET.get('familia', 'TODAS')
    
    if familia_activa != 'TODAS':
        oportunidades_list = [o for o in oportunidades_list if o.familia == familia_activa]

    total_ahorro = sum(o.ahorro_potencial for o in oportunidades_list)
    ahorro_mensual = total_ahorro / 12

    context = {
        'oportunidades': oportunidades_list,
        'familias': familias,
        'familia_activa': familia_activa,
        'total_ahorro': total_ahorro,
        'ahorro_mensual': ahorro_mensual,
        'total_referencias': len(oportunidades_list),
        'active_tab': 'dashboard', # Ilumina "Dashboard" en el menú
        'segmento': 'EFP',         # Mantiene el sidebar en modo EFP
    }
    return render(request, 'efp/dashboard.html', context)

# --- BUSCADOR ---
@login_required(login_url='login')
def buscador(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    query = request.GET.get('q', '')
    resultados = []
    
    if query:
        # Buscamos por nombre del grupo (síntoma) o por productos a sustituir
        resultados = OportunidadEFP.objects.filter(farmacia_id=f_id).filter(
            Q(nombre_grupo__icontains=query) | 
            Q(a_sustituir__icontains=query) |
            Q(producto_recomendado__icontains=query)
        )
    
    context = {
        'query': query,
        'resultados': resultados,
        'active_tab': 'buscador',
        'segmento': 'EFP'
    }
    return render(request, 'efp/buscador.html', context)

# --- DATOS BRUTOS ---
@login_required(login_url='login')
def datos_brutos(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    
    # 1. Capturar orden
    order_param = request.GET.get('order', '-ahorro_potencial')
    
    # 2. Lista blanca de campos permitidos (Seguridad)
    campos_validos = [
        'nombre_grupo', '-nombre_grupo',
        'producto_recomendado', '-producto_recomendado',
        'pvp_medio', '-pvp_medio',
        'margen_pct', '-margen_pct',
        'ahorro_potencial', '-ahorro_potencial'
    ]
    
    orden_final = order_param if order_param in campos_validos else '-ahorro_potencial'

    # 3. Query Ordenada
    datos = OportunidadEFP.objects.filter(farmacia_id=f_id).order_by(orden_final)
    
    context = {
        'datos': datos,
        'active_tab': 'datos_brutos',
        'segmento': 'EFP',
        'current_order': orden_final # Pasamos el orden para las flechas
    }
    return render(request, 'efp/datos_brutos.html', context)

# --- CONFIGURACIÓN ---
@login_required(login_url='login')
def configuracion(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    
    # 1. Procesar Guardado
    if request.method == 'POST':
        id_agrupacion = request.POST.get('id_agrupacion')
        producto = request.POST.get('producto')
        
        if id_agrupacion:
            if producto:
                PreferenciaEFP.objects.update_or_create(
                    farmacia_id=f_id,
                    id_agrupacion=id_agrupacion,
                    defaults={'producto_preferido': producto}
                )
            else:
                # Si viene vacío o "Automático", borramos
                PreferenciaEFP.objects.filter(farmacia_id=f_id, id_agrupacion=id_agrupacion).delete()
        
        return redirect('efp_configuracion')

    # 2. Cargar datos para la vista
    qs = OportunidadEFP.objects.filter(farmacia_id=f_id).order_by('nombre_grupo')
    prefs = { p.id_agrupacion: p.producto_preferido for p in PreferenciaEFP.objects.filter(farmacia_id=f_id) }
    
    lista_config = []
    for item in qs:
        opciones = [item.producto_recomendado]
        stats = item.get_competidores_stats()
        for s in stats:
            if s['nombre'] not in opciones:
                opciones.append(s['nombre'])
        
        valor_actual = prefs.get(item.id_agrupacion, item.producto_recomendado)
        es_manual = item.id_agrupacion in prefs
        
        lista_config.append({
            'item': item,
            'valor_actual': valor_actual,
            'es_manual': es_manual,
            'opciones': sorted(opciones)
        })

    context = {
        'lista_config': lista_config,
        'active_tab': 'configuracion',
        'segmento': 'EFP'
    }
    return render(request, 'efp/configuracion.html', context)

# --- ENTRENAMIENTO ---
@login_required(login_url='login')
def entrenamiento(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    
    items_qs = OportunidadEFP.objects.filter(farmacia_id=f_id)
    if not items_qs.exists():
        return redirect('efp_dashboard')

    item = items_qs.order_by('?').first()
    
    # En EFP preguntamos por el GRUPO/SÍNTOMA
    marca_ask = item.nombre_grupo

    context = {
        'item': item,
        'marca_ask': marca_ask,
        'active_tab': 'entrenamiento',
        'segmento': 'EFP',
    }
    return render(request, 'efp/entrenamiento.html', context)

# --- EXAMEN ---
@login_required(login_url='login')
def examen(request):
    f_id = request.session.get('farmacia_activa', 'HF280050001')
    MAX_PREGUNTAS = 10 

    # 1. Inicialización / Reset
    if 'reset' in request.GET or 'efp_stats' not in request.session:
        request.session['efp_stats'] = {'aciertos': 0, 'total': 0, 'finalizado': False}
        if 'pregunta_actual' in request.session:
            del request.session['pregunta_actual']
        if 'reset' in request.GET:
            return redirect('efp_examen')

    stats = request.session['efp_stats']

    # 2. Control de Fin de Juego
    if stats['total'] >= MAX_PREGUNTAS:
        score = (stats['aciertos'] / MAX_PREGUNTAS) * 100
        if score == 100: feedback_text = "¡Eres un experto en Venta Libre! 🌟"
        elif score >= 50: feedback_text = "Buen trabajo, sigue practicando. 💪"
        else: feedback_text = "Revisa los márgenes y grupos de las EFP. ¡Ánimo! 📚"
        
        context = {
            'finalizado': True,
            'aciertos': stats['aciertos'],
            'total': MAX_PREGUNTAS,
            'score': score,
            'feedback': feedback_text,
            'active_tab': 'examen',
            'segmento': 'EFP',
        }
        return render(request, 'efp/examen.html', context)

    # 3. Lógica "Siguiente Pregunta" (Resetear estado para nueva ronda)
    if request.method == 'POST' and 'siguiente_pregunta' in request.POST:
        if 'pregunta_actual' in request.session:
            del request.session['pregunta_actual']
        return redirect('efp_examen')

    # 4. Generación de Pregunta (Si no existe una activa)
    if 'pregunta_actual' not in request.session:
        nueva_pregunta = generar_pregunta_examen(f_id)
        if not nueva_pregunta:
            # Caso borde: No hay suficientes datos en la farmacia
            return render(request, 'efp/examen.html', {
                'error': "No hay suficientes datos de EFP para generar un examen. Sincroniza datos primero.",
                'active_tab': 'examen'
            })
        request.session['pregunta_actual'] = nueva_pregunta

    pregunta_data = request.session['pregunta_actual']
    
    # Variables de contexto por defecto (Modo: Esperando respuesta)
    mostrar_feedback = False
    es_correcto = False
    seleccion_usuario = None
    mensaje = ""

    # 5. Procesar Respuesta (POST)
    if request.method == 'POST' and 'opcion' in request.POST:
        seleccion_usuario = request.POST.get('opcion')
        correcto = pregunta_data['producto_correcto']
        mostrar_feedback = True # ¡Esto activa el modo revisión en el template!
        
        # Verificamos si ya se había contestado esta pregunta en esta sesión para no sumar doble
        # (Usamos un flag temporal en session o simplemente confiamos en el flujo)
        if 'pregunta_respondida_id' not in request.session or request.session['pregunta_respondida_id'] != pregunta_data['id_pregunta']:
            stats['total'] += 1
            if seleccion_usuario == correcto:
                stats['aciertos'] += 1
                es_correcto = True
                mensaje = "¡Correcto! Es la opción adecuada para este grupo."
            else:
                es_correcto = False
                mensaje = f"Incorrecto. {pregunta_data['explicacion']}"
            
            # Actualizamos sesión y marcamos como respondida
            request.session['efp_stats'] = stats
            request.session['pregunta_respondida_id'] = pregunta_data['id_pregunta']
        else:
            # Si el usuario refresca la página de resultado, recuperamos el estado anterior
            es_correcto = (seleccion_usuario == correcto)
            mensaje = "Ya respondiste a esta pregunta."

    # 6. Renderizar
    context = {
        'pregunta': pregunta_data,
        'mostrar_feedback': mostrar_feedback,
        'es_correcto': es_correcto,
        'seleccion_usuario': seleccion_usuario,
        'mensaje': mensaje,
        'aciertos': stats['aciertos'],
        'total_jugado': stats['total'], # Preguntas respondidas hasta ahora
        'total_max': MAX_PREGUNTAS,
        'active_tab': 'examen',
        'segmento': 'EFP',
        'finalizado': False
    }
    return render(request, 'efp/examen.html', context)

# --- GUARDAR PREFERENCIA (POST) ---
@login_required(login_url='login')
def set_preferencia_efp(request):
    if request.method == 'POST':
        f_id = request.session.get('farmacia_activa', 'HF280050001')
        id_agrupacion = request.POST.get('id_agrupacion')
        producto = request.POST.get('producto') 
        
        if producto:
            PreferenciaEFP.objects.update_or_create(
                farmacia_id=f_id,
                id_agrupacion=id_agrupacion,
                defaults={'producto_preferido': producto}
            )
        else:
            PreferenciaEFP.objects.filter(farmacia_id=f_id, id_agrupacion=id_agrupacion).delete()
            
        return redirect(request.POST.get('next', 'efp_dashboard'))
    return redirect('efp_dashboard')
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

    # 1. Reset
    if 'reset' in request.GET or 'efp_stats' not in request.session:
        request.session['efp_stats'] = {'aciertos': 0, 'total': 0}
        request.session.pop('pregunta_actual', None)
        request.session.pop('resultado_pendiente', None)
        request.session.modified = True
        if 'reset' in request.GET:
            return redirect('efp_examen')

    stats = request.session.get('efp_stats', {'aciertos': 0, 'total': 0})

    # 2. Verificar fin de examen
    if stats['total'] >= MAX_PREGUNTAS:
        score = (stats['aciertos'] / MAX_PREGUNTAS * 100) if stats['total'] > 0 else 0
        if score == 100: feedback_text = "¡Eres un experto en Venta Libre! 🌟"
        elif score >= 50: feedback_text = "Buen trabajo, sigue practicando. 💪"
        else: feedback_text = "Revisa los márgenes y grupos de las EFP. ¡Ánimo! 📚"
        
        request.session.pop('resultado_pendiente', None)
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

    # 3. Si hay resultado pendiente, mostrarlo y borrarlo
    resultado_pendiente = request.session.pop('resultado_pendiente', None)
    if resultado_pendiente:
        # También borra pregunta actual para que genere una nueva en el siguiente GET
        request.session.pop('pregunta_actual', None)
        request.session.modified = True
        context = resultado_pendiente
        return render(request, 'efp/examen.html', context)

    # 4. Procesar respuesta del usuario
    if request.method == 'POST' and 'opcion' in request.POST:
        pregunta_data = request.session.get('pregunta_actual')
        if pregunta_data:
            seleccion_usuario = request.POST.get('opcion')
            correcto = pregunta_data.get('producto_correcto')
            pregunta_texto = request.POST.get('pregunta_texto', pregunta_data.get('pregunta_texto', 'medicina'))
            
            # Asegurar encoding UTF-8
            if isinstance(seleccion_usuario, bytes):
                seleccion_usuario = seleccion_usuario.decode('utf-8')
            if isinstance(correcto, bytes):
                correcto = correcto.decode('utf-8')
            if isinstance(pregunta_texto, bytes):
                pregunta_texto = pregunta_texto.decode('utf-8')
            
            stats['total'] += 1
            if seleccion_usuario == correcto:
                stats['aciertos'] += 1
                es_correcto = True
                mensaje = "¡Correcto! Es la opción adecuada para este grupo."
            else:
                es_correcto = False
                mensaje = f"Incorrecto. El paciente pide: {pregunta_texto}. Tú elegiste: {seleccion_usuario}. La opción óptima es: {correcto}"
            
            request.session['efp_stats'] = stats
            request.session.pop('pregunta_actual', None)  # Borra pregunta actual para generar nueva
            
            # Guardar resultado para mostrar en siguiente render
            request.session['resultado_pendiente'] = {
                'pregunta': pregunta_data,
                'mensaje': mensaje,
                'es_correcto': es_correcto,
                'seleccion_usuario': seleccion_usuario,
                'aciertos': stats['aciertos'],
                'total_jugado': stats['total'],
                'total_max': MAX_PREGUNTAS,
                'mostrar_feedback_solo': True,
                'active_tab': 'examen',
                'segmento': 'EFP',
                'finalizado': False
            }
            request.session.modified = True
            
            # Redirect a GET para que procese resultado_pendiente
            return redirect('efp_examen')

    # 5. Generar nueva pregunta
    pregunta_data = request.session.get('pregunta_actual')
    if not pregunta_data:
        nueva_pregunta = generar_pregunta_examen(f_id)
        if not nueva_pregunta:
            # Se acabaron preguntas: fuerza fin de examen
            stats['total'] = MAX_PREGUNTAS
            request.session['efp_stats'] = stats
            request.session.modified = True
            
            score = (stats['aciertos'] / MAX_PREGUNTAS * 100)
            if score == 100: feedback_text = "¡Eres un experto en Venta Libre! 🌟"
            elif score >= 50: feedback_text = "Buen trabajo, sigue practicando. 💪"
            else: feedback_text = "Revisa los márgenes y grupos de las EFP. ¡Ánimo! 📚"
            
            context = {
                'finalizado': True,
                'aciertos': stats['aciertos'],
                'total': stats['total'],
                'score': score,
                'feedback': feedback_text,
                'active_tab': 'examen',
                'segmento': 'EFP',
            }
            return render(request, 'efp/examen.html', context)
        
        request.session['pregunta_actual'] = nueva_pregunta
        request.session.modified = True
        pregunta_data = nueva_pregunta

    # 6. Mostrar pregunta normal
    context = {
        'pregunta': pregunta_data,
        'mostrar_feedback_solo': False,
        'aciertos': stats['aciertos'],
        'total_jugado': stats['total'],
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
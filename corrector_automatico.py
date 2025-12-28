#!/usr/bin/env python
"""
CORRECTOR AUTOMATICO DE PROYECTO FARMA_DJANGO
==============================================

Este script detecta y corrige automáticamente los siguientes problemas:

CATEGORIAS DE PROBLEMAS:
1. REDUNDANCIAS - Código duplicado entre core y efp
2. INCONSISTENCIAS - Incoherencias en lógica o nomenclatura
3. ERRORES - Bugs, imports incorrectos, validaciones faltantes
4. OPTIMIZACIONES - Mejoras de rendimiento y buenas prácticas

MODO DE USO:
    python corrector_automatico.py --check     # Solo muestra problemas
    python corrector_automatico.py --fix       # Aplica correcciones
    python corrector_automatico.py --fix-one N # Corrige solo el problema N

IMPORTANTE:
- Cada corrección se aplica de una en una para verificar que la app sigue funcionando
- Después de cada corrección, ejecuta: python manage.py runserver
- Verifica que todo funciona antes de aplicar la siguiente
"""

import os
import sys
import re
from pathlib import Path
import difflib
from datetime import datetime

# ============================================================================
# CONFIGURACION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backups_correcciones"

# ============================================================================
# DEFINICION DE PROBLEMAS ENCONTRADOS
# ============================================================================

PROBLEMAS = [
    # ========================================================================
    # CATEGORIA 1: ERRORES CRITICOS
    # ========================================================================
    {
        'id': 1,
        'categoria': 'ERROR',
        'severidad': 'ALTA',
        'titulo': 'Modelo Preferencia sin campo farmacia_id',
        'descripcion': """
        El modelo Preferencia en core/models.py no tiene campo farmacia_id,
        lo que hace que las preferencias sean globales en vez de por farmacia.
        Esto causa conflictos cuando múltiples farmacias usan la app.
        """,
        'archivo': 'core/models.py',
        'linea': 97,
        'solucion': 'Añadir campo farmacia_id a Preferencia y crear migración',
        'codigo_antiguo': """class Preferencia(models.Model):
    grupo_homogeneo = models.CharField(max_length=255, unique=True)
    laboratorio_preferente = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.grupo_homogeneo} -> {self.laboratorio_preferente}" """,
        'codigo_nuevo': """class Preferencia(models.Model):
    grupo_homogeneo = models.CharField(max_length=255)
    laboratorio_preferente = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    farmacia_id = models.CharField(max_length=50, default='HF280050001')

    class Meta:
        unique_together = ('grupo_homogeneo', 'farmacia_id')

    def __str__(self):
        return f"{self.grupo_homogeneo} -> {self.laboratorio_preferente}" """,
        'migracion_requerida': True
    },
    
    {
        'id': 2,
        'categoria': 'ERROR',
        'severidad': 'ALTA',
        'titulo': 'Falta manejo de errores en obtener_farmacias_cloud()',
        'descripcion': """
        La función obtener_farmacias_cloud() en core/services.py no cierra
        la conexión a Databricks cuando hay un error, causando conexiones huérfanas.
        """,
        'archivo': 'core/services.py',
        'linea': 146,
        'solucion': 'Añadir try-finally para garantizar cierre de conexión',
        'codigo_antiguo': """def obtener_farmacias_cloud():
    try:
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        cursor = connection.cursor()
        
        query = \"\"\"
            SELECT FARMACIA_NOM 
            FROM cat_farma.datavaultperformance.nom_farmacias 
            WHERE ACTIVO = 1 
            ORDER BY FARMACIA_NOM
        \"\"\"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        lista = [row[0] for row in rows]
        return lista, None
        
    except Exception as e:
        print(f"ERROR DATABRICKS (Farmacias): {str(e)}")
        return [], str(e)""",
        'codigo_nuevo': """def obtener_farmacias_cloud():
    connection = None
    cursor = None
    try:
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        cursor = connection.cursor()
        
        query = \"\"\"
            SELECT FARMACIA_NOM 
            FROM cat_farma.datavaultperformance.nom_farmacias 
            WHERE ACTIVO = 1 
            ORDER BY FARMACIA_NOM
        \"\"\"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        lista = [row[0] for row in rows]
        return lista, None
        
    except Exception as e:
        print(f"ERROR DATABRICKS (Farmacias): {str(e)}")
        return [], str(e)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()""",
        'migracion_requerida': False
    },

    {
        'id': 3,
        'categoria': 'ERROR',
        'severidad': 'MEDIA',
        'titulo': 'Doble llamada a obtener_farmacias_cloud() en view importar',
        'descripcion': """
        En core/views.py, función importar(), se llama dos veces a 
        obtener_farmacias_cloud() desperdiciando recursos y tiempo.
        Líneas 388-395 y 398 duplicadas.
        """,
        'archivo': 'core/views.py',
        'linea': 388,
        'solucion': 'Eliminar primera llamada duplicada',
        'codigo_antiguo': """    # --- OPTIMIZACIÓN: CACHÉ DE FARMACIAS ---
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
    
    # 1. AHORA SÍ LLAMAMOS A LA FUNCIÓN REAL
    lista_farmacias_cloud, error_cloud = obtener_farmacias_cloud()
    
    mensaje = None
    tipo_mensaje = ""
    
    if error_cloud:
         mensaje = f"Error conectando a Databricks: {error_cloud}"
         tipo_mensaje = "warning\"""",
        'codigo_nuevo': """    # --- OPTIMIZACIÓN: CACHÉ DE FARMACIAS ---
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
         tipo_mensaje = "warning\"""",
        'migracion_requerida': False
    },

    {
        'id': 4,
        'categoria': 'ERROR',
        'severidad': 'MEDIA',
        'titulo': 'Variables mensaje y tipo_mensaje duplicadas',
        'descripcion': """
        En core/views.py línea 392-396, las variables mensaje y tipo_mensaje
        se inicializan dos veces seguidas sin razón.
        """,
        'archivo': 'core/views.py',
        'linea': 392,
        'solucion': 'Ya está incluido en corrección #3',
        'aplicar': False
    },

    # ========================================================================
    # CATEGORIA 2: REDUNDANCIAS
    # ========================================================================
    {
        'id': 5,
        'categoria': 'REDUNDANCIA',
        'severidad': 'MEDIA',
        'titulo': 'Método get_competidores_stats() duplicado',
        'descripcion': """
        Los modelos Oportunidad (core) y OportunidadEFP (efp) tienen
        implementaciones casi idénticas de get_competidores_stats().
        Esto dificulta el mantenimiento y puede causar inconsistencias.
        """,
        'archivo': 'MULTIPLE',
        'linea': 'core/models.py:30, efp/models.py:46',
        'solucion': 'Crear clase abstracta base o mixin compartido',
        'codigo_antiguo': None,  # Ver archivos individuales
        'codigo_nuevo': """# Crear nuevo archivo: core/mixins.py

from django.db import models
import re

class CompetidoresStatsMixin:
    \"\"\"
    Mixin compartido para parsear estadísticas de competidores
    en formato: 'Marca (Unidades|Margen%) || Marca2 (...)'
    \"\"\"
    
    def get_competidores_stats(self):
        stats = []
        
        # Validar que exista el campo a_sustituir
        if not hasattr(self, 'a_sustituir') or not self.a_sustituir:
            return []
        
        items = self.a_sustituir.split(' || ')
        total_competencia = 0
        
        # ... (implementación unificada)
        return stats""",
        'migracion_requerida': False,
        'archivos_afectados': ['core/models.py', 'efp/models.py', 'core/mixins.py (nuevo)']
    },

    {
        'id': 6,
        'categoria': 'REDUNDANCIA',
        'severidad': 'BAJA',
        'titulo': 'Lógica de sincronización Databricks duplicada',
        'descripcion': """
        core/services.py y efp/services.py tienen código muy similar para:
        - Conectar a Databricks
        - Ejecutar query
        - Procesar resultados
        - Manejo de errores
        Solo cambia la query SQL y el modelo destino.
        """,
        'archivo': 'core/services.py, efp/services.py',
        'linea': 'Funciones sincronizar_*',
        'solucion': 'Crear función genérica sincronizar_databricks(query, modelo, parser)',
        'aplicar': False,  # Requiere refactoring profundo
        'recomendacion': 'Implementar en siguiente fase de refactoring'
    },

    {
        'id': 7,
        'categoria': 'REDUNDANCIA',
        'severidad': 'BAJA',
        'titulo': 'Templates casi idénticos entre core y efp',
        'descripcion': """
        Los templates dashboard.html, entrenamiento.html, examen.html son
        casi iguales entre core/templates/ y efp/templates/.
        Solo cambian pequeños detalles como títulos y colores.
        """,
        'archivo': 'TEMPLATES',
        'solucion': 'Crear templates base unificados con variables condicionales',
        'aplicar': False,
        'recomendacion': 'Implementar en siguiente fase (requiere cambios en múltiples templates)'
    },

    # ========================================================================
    # CATEGORIA 3: INCONSISTENCIAS
    # ========================================================================
    {
        'id': 8,
        'categoria': 'INCONSISTENCIA',
        'severidad': 'BAJA',
        'titulo': 'Nombre inconsistente de campo en Preferencia',
        'descripcion': """
        PreferenciaEFP usa 'producto_preferido' pero Preferencia usa
        'laboratorio_preferente'. Deberían usar la misma nomenclatura.
        """,
        'archivo': 'core/models.py, efp/models.py',
        'linea': '97, 100',
        'solucion': 'Unificar a "producto_preferido" en ambos modelos',
        'aplicar': False,
        'migracion_requerida': True,
        'recomendacion': 'Cambio cosmético, aplicar solo si se hace migración grande'
    },

    {
        'id': 9,
        'categoria': 'INCONSISTENCIA',
        'severidad': 'MEDIA',
        'titulo': 'Filtrado de preferencias inconsistente',
        'descripcion': """
        En core/views.py, entrenamiento() filtra Preferencia solo por 
        grupo_homogeneo (línea 173), pero debería filtrar también por farmacia_id.
        Esto puede mostrar preferencias de otras farmacias.
        """,
        'archivo': 'core/views.py',
        'linea': 173,
        'solucion': 'Añadir farmacia_id al filtro de Preferencia',
        'codigo_antiguo': """    try:
        pref = Preferencia.objects.get(grupo_homogeneo=item.grupo_homogeneo, activo=True)
        producto_final = f"{pref.laboratorio_preferente} (Preferencia)"
        es_preferencia = True""",
        'codigo_nuevo': """    try:
        pref = Preferencia.objects.get(
            grupo_homogeneo=item.grupo_homogeneo, 
            farmacia_id=f_id,
            activo=True
        )
        producto_final = f"{pref.laboratorio_preferente} (Preferencia)"
        es_preferencia = True""",
        'dependencias': [1],  # Requiere que problema #1 esté resuelto
        'migracion_requerida': False
    },

    {
        'id': 10,
        'categoria': 'INCONSISTENCIA',
        'severidad': 'MEDIA',
        'titulo': 'Mismo problema en vista examen()',
        'descripcion': """
        La vista examen() en core/views.py también consulta Preferencia
        sin filtrar por farmacia_id (línea 247).
        """,
        'archivo': 'core/views.py',
        'linea': 247,
        'solucion': 'Añadir farmacia_id al filtro',
        'codigo_antiguo': """        try:
            pref = Preferencia.objects.get(grupo_homogeneo=posible_item.grupo_homogeneo, activo=True)
            respuesta_correcta = pref.laboratorio_preferente
            origen = "Preferencia\"""",
        'codigo_nuevo': """        try:
            pref = Preferencia.objects.get(
                grupo_homogeneo=posible_item.grupo_homogeneo,
                farmacia_id=f_id,
                activo=True
            )
            respuesta_correcta = pref.laboratorio_preferente
            origen = "Preferencia\"""",
        'dependencias': [1],
        'migracion_requerida': False
    },

    {
        'id': 11,
        'categoria': 'INCONSISTENCIA',
        'severidad': 'MEDIA',
        'titulo': 'Vista configuracion() también sin filtro farmacia',
        'descripcion': """
        En core/views.py línea 298, configuracion() obtiene todas las
        Preferencia sin filtrar por farmacia.
        """,
        'archivo': 'core/views.py',
        'linea': 298,
        'solucion': 'Filtrar por farmacia_id',
        'codigo_antiguo': """    preferencias_dict = {
        p.grupo_homogeneo: p 
        for p in Preferencia.objects.filter(activo=True)
    }""",
        'codigo_nuevo': """    preferencias_dict = {
        p.grupo_homogeneo: p 
        for p in Preferencia.objects.filter(farmacia_id=f_id, activo=True)
    }""",
        'dependencias': [1],
        'migracion_requerida': False
    },

    {
        'id': 12,
        'categoria': 'INCONSISTENCIA',
        'severidad': 'BAJA',
        'titulo': 'Guardar Preferencia sin farmacia_id',
        'descripcion': """
        En core/views.py línea 305-310, cuando se guarda una preferencia
        no se incluye el farmacia_id.
        """,
        'archivo': 'core/views.py',
        'linea': 305,
        'solucion': 'Añadir farmacia_id al create/update',
        'codigo_antiguo': """        if grupo and producto_elegido:
            Preferencia.objects.update_or_create(
                grupo_homogeneo=grupo,
                defaults={'laboratorio_preferente': producto_elegido, 'activo': is_active}
            )""",
        'codigo_nuevo': """        if grupo and producto_elegido:
            Preferencia.objects.update_or_create(
                grupo_homogeneo=grupo,
                farmacia_id=f_id,
                defaults={'laboratorio_preferente': producto_elegido, 'activo': is_active}
            )""",
        'dependencias': [1],
        'migracion_requerida': False
    },

    # ========================================================================
    # CATEGORIA 4: OPTIMIZACIONES Y MEJORAS
    # ========================================================================
    {
        'id': 13,
        'categoria': 'OPTIMIZACION',
        'severidad': 'BAJA',
        'titulo': 'Imports no utilizados en core/views.py',
        'descripcion': """
        La línea 8 importa PreferenciaForm que nunca se usa en el archivo.
        """,
        'archivo': 'core/views.py',
        'linea': 8,
        'solucion': 'Eliminar import no usado',
        'codigo_antiguo': """from .forms import PreferenciaForm""",
        'codigo_nuevo': """# PreferenciaForm no se usa en este archivo""",
        'migracion_requerida': False
    },

    {
        'id': 14,
        'categoria': 'OPTIMIZACION',
        'severidad': 'BAJA',
        'titulo': 'Import duplicado de sincronizar_desde_databricks',
        'descripcion': """
        En core/views.py, línea 9 y 11 importan la misma función dos veces.
        """,
        'archivo': 'core/views.py',
        'linea': 9,
        'solucion': 'Eliminar import duplicado',
        'codigo_antiguo': """from .services import sincronizar_desde_databricks
from efp.services import sincronizar_efp_desde_databricks
from core.services import sincronizar_desde_databricks, obtener_farmacias_cloud""",
        'codigo_nuevo': """from .services import sincronizar_desde_databricks, obtener_farmacias_cloud
from efp.services import sincronizar_efp_desde_databricks""",
        'migracion_requerida': False
    },

    {
        'id': 15,
        'categoria': 'OPTIMIZACION',
        'severidad': 'MEDIA',
        'titulo': 'Query N+1 en dashboard view',
        'descripcion': """
        En core/views.py dashboard(), líneas 59-62 hacen un loop calculando
        marcas_a_sustituir, ejecutando get_competidores_stats() para cada
        oportunidad. Esto es ineficiente con muchos registros.
        """,
        'archivo': 'core/views.py',
        'linea': 59,
        'solucion': 'Calcular en la query SQL o usar agregación Django',
        'aplicar': False,
        'recomendacion': 'Optimización avanzada, aplicar si hay problemas de rendimiento'
    },

    {
        'id': 16,
        'categoria': 'OPTIMIZACION',
        'severidad': 'BAJA',
        'titulo': 'Falta índice en campo farmacia_id',
        'descripcion': """
        El campo farmacia_id en Oportunidad no tiene db_index=True,
        ralentizando queries de filtrado (que son muy frecuentes).
        """,
        'archivo': 'core/models.py',
        'linea': 25,
        'solucion': 'Añadir db_index=True',
        'codigo_antiguo': """    farmacia_id = models.CharField(max_length=50, default='HF280050001')""",
        'codigo_nuevo': """    farmacia_id = models.CharField(max_length=50, default='HF280050001', db_index=True)""",
        'migracion_requerida': True
    },

    {
        'id': 17,
        'categoria': 'OPTIMIZACION',
        'severidad': 'BAJA',
        'titulo': 'Ordenación redundante en configuracion()',
        'descripcion': """
        En core/views.py línea 319, se ordenan opciones con sorted()
        cuando ya están implícitamente ordenadas por el loop.
        """,
        'archivo': 'core/views.py',
        'linea': 319,
        'solucion': 'Remover sorted() o justificar necesidad',
        'aplicar': False,
        'recomendacion': 'Mejora menor, aplicar en fase de pulido'
    },

    # ========================================================================
    # CATEGORIA 5: SEGURIDAD Y VALIDACIONES
    # ========================================================================
    {
        'id': 18,
        'categoria': 'SEGURIDAD',
        'severidad': 'MEDIA',
        'titulo': 'Falta validación de entrada en cambiar_farmacia',
        'descripcion': """
        En core/views.py línea 89-93, cambiar_farmacia() no valida que
        el farmacia_id recibido exista realmente antes de guardarlo en sesión.
        Un usuario malintencionado podría inyectar IDs falsos.
        """,
        'archivo': 'core/views.py',
        'linea': 89,
        'solucion': 'Validar que farmacia_id existe en base de datos',
        'codigo_antiguo': """@staff_member_required
def cambiar_farmacia(request):
    if request.method == 'POST':
        nueva_farmacia = request.POST.get('farmacia_id')
        if nueva_farmacia:
            request.session['farmacia_activa'] = nueva_farmacia
    
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))""",
        'codigo_nuevo': """@staff_member_required
def cambiar_farmacia(request):
    if request.method == 'POST':
        nueva_farmacia = request.POST.get('farmacia_id')
        if nueva_farmacia:
            # Validar que la farmacia existe
            if Oportunidad.objects.filter(farmacia_id=nueva_farmacia).exists():
                request.session['farmacia_activa'] = nueva_farmacia
            else:
                from django.contrib import messages
                messages.warning(request, f"Farmacia {nueva_farmacia} no encontrada")
    
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))""",
        'migracion_requerida': False
    },

    {
        'id': 19,
        'categoria': 'SEGURIDAD',
        'severidad': 'ALTA',
        'titulo': 'DEBUG=True en producción',
        'descripcion': """
        En config/settings.py línea 27, DEBUG está hardcodeado a True.
        Esto expone información sensible en producción.
        """,
        'archivo': 'config/settings.py',
        'linea': 27,
        'solucion': 'Usar variable de entorno',
        'codigo_antiguo': """DEBUG = True
# DEBUG = os.environ.get("DEBUG", "False") == "True\"""",
        'codigo_nuevo': """# DEBUG debe ser False en producción
DEBUG = os.environ.get("DEBUG", "False") == "True\"""",
        'migracion_requerida': False
    },

    {
        'id': 20,
        'categoria': 'SEGURIDAD',
        'severidad': 'MEDIA',
        'titulo': 'ALLOWED_HOSTS vacío',
        'descripcion': """
        En config/settings.py línea 31, ALLOWED_HOSTS está vacío,
        lo cual es inseguro en producción.
        """,
        'archivo': 'config/settings.py',
        'linea': 31,
        'solucion': 'Usar variable de entorno',
        'codigo_antiguo': """ALLOWED_HOSTS = []
# ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")""",
        'codigo_nuevo': """# En producción debe tener el dominio real
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")""",
        'migracion_requerida': False
    },

    # ========================================================================
    # CATEGORIA 6: DOCUMENTACION Y COMENTARIOS
    # ========================================================================
    {
        'id': 21,
        'categoria': 'DOCUMENTACION',
        'severidad': 'BAJA',
        'titulo': 'Función sin docstring en get_competidores_stats',
        'descripcion': """
        El método get_competidores_stats() en ambos modelos tiene docstring
        básico pero no explica el formato de retorno ni parámetros esperados.
        """,
        'archivo': 'core/models.py, efp/models.py',
        'solucion': 'Mejorar docstring con formato Google o NumPy style',
        'aplicar': False,
        'recomendacion': 'Mejora de documentación, baja prioridad'
    },

    {
        'id': 22,
        'categoria': 'DOCUMENTACION',
        'severidad': 'BAJA',
        'titulo': 'Comentarios en español e inglés mezclados',
        'descripcion': """
        A lo largo del proyecto hay comentarios en español y en inglés
        mezclados sin consistencia.
        """,
        'archivo': 'TODOS',
        'solucion': 'Estandarizar a un solo idioma',
        'aplicar': False,
        'recomendacion': 'Mejora estética, baja prioridad'
    }
]

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def crear_backup(archivo_path):
    """Crea backup de un archivo antes de modificarlo"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = Path(archivo_path)
    if archivo.exists():
        backup_path = BACKUP_DIR / f"{archivo.stem}_{timestamp}{archivo.suffix}.bak"
        import shutil
        shutil.copy2(archivo, backup_path)
        return backup_path
    return None

def mostrar_diff(texto_viejo, texto_nuevo):
    """Muestra diff colorizado entre dos textos"""
    diff = list(difflib.unified_diff(
        texto_viejo.splitlines(keepends=True),
        texto_nuevo.splitlines(keepends=True),
        fromfile='anterior',
        tofile='nuevo'
    ))
    
    for line in diff:
        if line.startswith('+'):
            print(f"\033[92m{line}\033[0m", end='')
        elif line.startswith('-'):
            print(f"\033[91m{line}\033[0m", end='')
        elif line.startswith('@'):
            print(f"\033[94m{line}\033[0m", end='')
        else:
            print(line, end='')

def aplicar_correccion(problema):
    """Aplica la corrección de un problema específico"""
    print(f"\n{'='*80}")
    print(f"APLICANDO CORRECCIÓN #{problema['id']}")
    print(f"Título: {problema['titulo']}")
    print(f"{'='*80}\n")
    
    if not problema.get('aplicar', True):
        print("⚠️  Esta corrección está marcada como NO APLICAR automáticamente")
        print(f"Recomendación: {problema.get('recomendacion', 'Revisar manualmente')}")
        return False
    
    archivo_path = BASE_DIR / problema['archivo']
    
    if not archivo_path.exists():
        print(f"❌ Error: Archivo {archivo_path} no encontrado")
        return False
    
    # Crear backup
    backup = crear_backup(archivo_path)
    print(f"✅ Backup creado: {backup}")
    
    # Leer contenido actual
    with open(archivo_path, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Verificar que el código antiguo existe
    if problema.get('codigo_antiguo'):
        if problema['codigo_antiguo'].strip() not in contenido:
            print(f"❌ Error: No se encontró el código antiguo en el archivo")
            print(f"Buscando:\n{problema['codigo_antiguo'][:100]}...")
            return False
    
    # Aplicar cambio
    nuevo_contenido = contenido.replace(
        problema['codigo_antiguo'],
        problema['codigo_nuevo']
    )
    
    # Mostrar diff
    print("\n📝 Cambios a aplicar:")
    print("-" * 80)
    mostrar_diff(contenido, nuevo_contenido)
    print("-" * 80)
    
    # Guardar cambios
    with open(archivo_path, 'w', encoding='utf-8') as f:
        f.write(nuevo_contenido)
    
    print(f"\n✅ Corrección aplicada en: {archivo_path}")
    
    if problema.get('migracion_requerida'):
        print("\n⚠️  ATENCIÓN: Esta corrección requiere crear una migración")
        print("Ejecuta: python manage.py makemigrations")
        print("         python manage.py migrate")
    
    return True

def mostrar_resumen():
    """Muestra resumen de todos los problemas"""
    print("\n" + "="*80)
    print(" " * 20 + "REPORTE DE PROBLEMAS DETECTADOS")
    print("="*80 + "\n")
    
    por_categoria = {}
    for p in PROBLEMAS:
        cat = p['categoria']
        if cat not in por_categoria:
            por_categoria[cat] = []
        por_categoria[cat].append(p)
    
    for categoria, problemas in sorted(por_categoria.items()):
        print(f"\n📁 {categoria} ({len(problemas)} problemas)")
        print("-" * 80)
        
        for p in problemas:
            severidad_color = {
                'ALTA': '\033[91m',    # Rojo
                'MEDIA': '\033[93m',   # Amarillo
                'BAJA': '\033[92m'     # Verde
            }.get(p['severidad'], '')
            
            aplicable = "✅" if p.get('aplicar', True) else "⚠️ "
            
            print(f"  {aplicable} #{p['id']:2d} [{severidad_color}{p['severidad']:5s}\033[0m] {p['titulo']}")
            print(f"       {p['archivo']} : línea {p.get('linea', '?')}")
            if not p.get('aplicar', True):
                print(f"       💡 {p.get('recomendacion', 'Revisar manualmente')}")
    
    print("\n" + "="*80)
    print(f"TOTAL: {len(PROBLEMAS)} problemas detectados")
    print("="*80 + "\n")

def mostrar_ayuda():
    """Muestra ayuda de uso"""
    print(__doc__)

# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Corrector automático del proyecto FARMA_DJANGO',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python corrector_automatico.py --check           # Ver todos los problemas
  python corrector_automatico.py --fix             # Corregir todos (interactivo)
  python corrector_automatico.py --fix-one 1       # Corregir solo problema #1
  python corrector_automatico.py --fix-range 1 5   # Corregir problemas 1-5
  python corrector_automatico.py --export          # Exportar reporte a archivo
        """
    )
    
    parser.add_argument('--check', action='store_true',
                        help='Mostrar listado de problemas sin corregir')
    parser.add_argument('--fix', action='store_true',
                        help='Aplicar todas las correcciones (interactivo)')
    parser.add_argument('--fix-one', type=int, metavar='N',
                        help='Aplicar solo la corrección N')
    parser.add_argument('--fix-range', nargs=2, type=int, metavar=('START', 'END'),
                        help='Aplicar correcciones desde START hasta END')
    parser.add_argument('--export', type=str, metavar='FILE',
                        help='Exportar reporte a archivo')
    parser.add_argument('--force', action='store_true',
                        help='No pedir confirmación (usar con precaución)')
    
    args = parser.parse_args()
    
    # Sin argumentos, mostrar ayuda
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # Modo check: solo listar
    if args.check:
        mostrar_resumen()
        return
    
    # Modo export
    if args.export:
        with open(args.export, 'w', encoding='utf-8') as f:
            f.write("REPORTE DE PROBLEMAS - FARMA_DJANGO\n")
            f.write("=" * 80 + "\n\n")
            for p in PROBLEMAS:
                f.write(f"ID: {p['id']}\n")
                f.write(f"Categoría: {p['categoria']} - Severidad: {p['severidad']}\n")
                f.write(f"Título: {p['titulo']}\n")
                f.write(f"Archivo: {p['archivo']} (línea {p.get('linea', '?')})\n")
                f.write(f"Descripción: {p['descripcion']}\n")
                f.write(f"Solución: {p['solucion']}\n")
                f.write("-" * 80 + "\n\n")
        print(f"✅ Reporte exportado a: {args.export}")
        return
    
    # Modo fix-one
    if args.fix_one:
        problema = next((p for p in PROBLEMAS if p['id'] == args.fix_one), None)
        if not problema:
            print(f"❌ Error: No existe el problema #{args.fix_one}")
            return
        
        if not args.force:
            print(f"\n¿Aplicar corrección #{problema['id']}?")
            print(f"Título: {problema['titulo']}")
            respuesta = input("Confirmar (s/n): ")
            if respuesta.lower() != 's':
                print("Cancelado")
                return
        
        aplicar_correccion(problema)
        return
    
    # Modo fix-range
    if args.fix_range:
        start, end = args.fix_range
        problemas_rango = [p for p in PROBLEMAS if start <= p['id'] <= end]
        
        print(f"\nSe aplicarán {len(problemas_rango)} correcciones")
        if not args.force:
            respuesta = input("Confirmar (s/n): ")
            if respuesta.lower() != 's':
                print("Cancelado")
                return
        
        for p in problemas_rango:
            aplicar_correccion(p)
            input("\nPresiona ENTER para continuar con la siguiente corrección...")
        return
    
    # Modo fix: aplicar todas
    if args.fix:
        aplicables = [p for p in PROBLEMAS if p.get('aplicar', True)]
        print(f"\nSe aplicarán {len(aplicables)} correcciones de {len(PROBLEMAS)} totales")
        
        if not args.force:
            respuesta = input("Confirmar (s/n): ")
            if respuesta.lower() != 's':
                print("Cancelado")
                return
        
        for p in aplicables:
            aplicar_correccion(p)
            input("\n⏸  Presiona ENTER para continuar (verifica que todo funciona)...")
        
        print("\n" + "="*80)
        print("🎉 ¡Todas las correcciones han sido aplicadas!")
        print("="*80)
        print("\n📋 PASOS SIGUIENTES:")
        print("1. Ejecutar: python manage.py makemigrations")
        print("2. Ejecutar: python manage.py migrate")
        print("3. Ejecutar: python manage.py runserver")
        print("4. Verificar que la aplicación funciona correctamente")
        print("\n💾 Los backups están en:", BACKUP_DIR)

if __name__ == '__main__':
    main()

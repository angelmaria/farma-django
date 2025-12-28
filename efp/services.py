# efp/services.py
import os
import json
import random
import re
from django.conf import settings
from databricks import sql
from django.db import transaction
from .models import OportunidadEFP
from dotenv import load_dotenv

load_dotenv()

# Mapeo de Iconos para las 14 Superfamilias (Para usar en el Template luego)
ICONOS_FAMILIAS = {
    "SISTEMA RESPIRATORIO": "fa-lungs",
    "SISTEMA DIGESTIVO": "fa-utensils",
    "SISTEMA NERVIOSO": "fa-brain",
    "DERMATOLOGÍA": "fa-hand-dots",
    "SISTEMA CIRCULATORIO": "fa-heart-pulse",
    "SALUD ÍNTIMA": "fa-venus-mars",
    "OFTALMOLOGÍA": "fa-eye",
    "BUCOFARÍNGEOS": "fa-lips", # O fa-tooth
    "CONTROL DE PESO": "fa-weight-scale",
    "TERAPIA NICOTINA": "fa-ban-smoking",
    "SALUD CAPILAR": "fa-scissors", # O fa-user-hair
    "COMPLEMENTOS": "fa-pills",
    "SISTEMA URINARIO": "fa-droplet",
    "HIGIENE OÍDO": "fa-ear-listen"
}

def cargar_jerarquia_local():
    """
    Mapeo manual de IDs a las 14 Superfamilias definidas.
    Clave: ID (int) -> Valor: (FAMILIA, SUBFAMILIA/NOMBRE)
    """
    path = os.path.join(settings.BASE_DIR, 'efp', 'data', 'efp_grupos.json')
    mapa = {}
    
    # Cargamos nombres del JSON si existe para usarlos de subfamilia
    nombres_json = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'grupos' in data:
                for g in data['grupos']:
                    nombres_json[g['id']] = g.get('nombre', 'Desconocido')
    except: pass

    # --- MAPEO MANUAL EXACTO ---
    # 1. SISTEMA RESPIRATORIO
    for i in [1, 2, 3, 5, 6, 7, 75, 77, 78, 79]: 
        mapa[i] = "SISTEMA RESPIRATORIO"
        
    # 2. SISTEMA DIGESTIVO
    for i in [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 54, 67, 71, 80, 86, 87, 88]: 
        mapa[i] = "SISTEMA DIGESTIVO"

    # 3. SISTEMA NERVIOSO (Incluimos Dolor e Insomnio aquí)
    for i in [20, 21, 22, 23, 24, 25, 26, 27, 28, 81, 85, 89]: 
        mapa[i] = "SISTEMA NERVIOSO"

    # 4. DERMATOLOGÍA
    for i in [29, 30, 31, 32, 33, 34, 35, 56, 57, 69, 72, 73, 74]: 
        mapa[i] = "DERMATOLOGÍA"

    # 5. SISTEMA CIRCULATORIO
    for i in [36, 37]: 
        mapa[i] = "SISTEMA CIRCULATORIO"

    # 6. SALUD ÍNTIMA
    for i in [38, 39, 55, 70, 83, 84]: 
        mapa[i] = "SALUD ÍNTIMA"

    # 7. OFTALMOLOGÍA
    for i in [8, 40]: 
        mapa[i] = "OFTALMOLOGÍA"

    # 8. BUCOFARÍNGEOS
    for i in [41, 42]: 
        mapa[i] = "BUCOFARÍNGEOS"

    # 9. CONTROL DE PESO
    for i in [43, 44]: 
        mapa[i] = "CONTROL DE PESO"

    # 10. TERAPIA NICOTINA
    for i in [45, 46, 47, 48]: 
        mapa[i] = "TERAPIA NICOTINA"

    # 11. SALUD CAPILAR
    for i in [49, 68, 82]: # 68 es Caspa
        mapa[i] = "SALUD CAPILAR"

    # 12. COMPLEMENTOS
    for i in [50]: 
        mapa[i] = "COMPLEMENTOS"

    # 13. SISTEMA URINARIO
    for i in [51]: 
        mapa[i] = "SISTEMA URINARIO"

    # 14. HIGIENE OÍDO
    for i in [52]: 
        mapa[i] = "HIGIENE OÍDO"

    # Construimos el diccionario final
    mapa_final = {}
    for id_g, familia in mapa.items():
        nombre = nombres_json.get(id_g, "Grupo EFP")
        mapa_final[id_g] = (familia, nombre)
        
    return mapa_final

def sincronizar_efp_desde_databricks(farmacia_id, fecha_inicio, fecha_fin):
    try:
        mapa_jerarquia = cargar_jerarquia_local()

        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        cursor = connection.cursor()

        query = f"""
        WITH Base_EFP AS (
            SELECT 
                bd.IdArticu,
                MAX(map.descripcion_articulo) as Nombre_Producto,
                MAX(ref.descripcion_grupo) as Nombre_Grupo_EFP,
                MAX(map.id_efp) as Id_Agrupacion,
                SUM(bd.Cantidad) as Unidades,
                SUM(bd.ImporteBruto) as Venta_Total,
                
                -- CORRECCIÓN 1: Usamos MAX(bd.PVP) para obtener el precio de catálogo real
                MAX(bd.PVP) as PVP_Medio_Real,
                
                -- Margen Unitario en Euros: (Venta - Coste) / Unidades
                ((SUM(bd.ImporteBruto) - SUM(COALESCE(bd.ImporteCoste, 0))) / NULLIF(SUM(bd.Cantidad),0)) as Margen_Unit_Eur,
                
                -- Margen %: (Venta - Coste) / Venta * 100
                CASE WHEN SUM(bd.ImporteBruto) > 0 THEN
                    ((SUM(bd.ImporteBruto) - SUM(COALESCE(bd.ImporteCoste, 0))) / SUM(bd.ImporteBruto)) * 100
                ELSE 0 END as Margen_Pct,
                
                SUM(COALESCE(bd.ImporteCoste, 0)) as Coste_Total
            FROM cat_farma.datavaultperformance.bridge_dispensacion bd
            INNER JOIN cat_farma.datavaultperformance.map_idArticu_idEfp map
                ON CAST(bd.IdArticu AS STRING) = CAST(map.id_articu AS STRING)
            INNER JOIN cat_farma.datavaultperformance.ref_efp ref
                ON map.id_efp = ref.idEfp
            WHERE bd.fecha >= DATE '{fecha_inicio}' AND bd.fecha < DATE '{fecha_fin}'
              AND bd.FARMACIA_NOM = '{farmacia_id}'
            GROUP BY bd.IdArticu
            HAVING SUM(bd.Cantidad) > 0
               AND Coste_Total > 0.1
               AND Margen_Pct < 99
        ),
        Ranked AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (PARTITION BY Id_Agrupacion ORDER BY Margen_Unit_Eur DESC) as Ranking,
                MAX(Margen_Unit_Eur) OVER (PARTITION BY Id_Agrupacion) as Mejor_Margen_Eur,
                -- Cálculo de cuota de mercado por agrupación
                (Unidades * 100.0) / SUM(Unidades) OVER (PARTITION BY Id_Agrupacion) as Cuota_Mercado
            FROM Base_EFP
        )
        SELECT 
            Id_Agrupacion,
            MAX(Nombre_Grupo_EFP),
            MAX(CASE WHEN Ranking = 1 THEN Nombre_Producto END), -- Producto Recomendado
            MAX(CASE WHEN Ranking = 1 THEN PVP_Medio_Real END),  -- PVP del Recomendado
            MAX(CASE WHEN Ranking = 1 THEN Margen_Pct END),      -- Margen del Recomendado
            SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)), -- Ahorro Potencial Total
            
            -- LISTA SUSTITUIBLES CON CN Y PVP
            array_join(collect_list(
                CASE 
                    WHEN Ranking > 1 
                    THEN concat(
                        coalesce(Nombre_Producto, 'Producto'), 
                        ' (', 
                        CAST(CAST(coalesce(Unidades, 0) AS INT) AS STRING), '###', 
                        CAST(CAST(ROUND(coalesce(Margen_Pct, 0), 0) AS INT) AS STRING), '###',
                        CAST(CAST(ROUND(coalesce(Cuota_Mercado, 0), 1) AS DECIMAL(10,1)) AS STRING), '###',
                        CAST(IdArticu AS STRING), '###', 
                        CAST(CAST(coalesce(PVP_Medio_Real, 0) AS DECIMAL(10,2)) AS STRING), -- AÑADIDO PVP
                        ')'
                    ) 
                END
            ), ' || '),
            
            MAX(CASE WHEN Ranking = 1 THEN IdArticu END) -- CN del Producto Recomendado

        FROM Ranked
        GROUP BY Id_Agrupacion
        HAVING SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)) > 10
        ORDER BY SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)) DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        with transaction.atomic():
            OportunidadEFP.objects.filter(farmacia_id=farmacia_id).delete()
            objs = []
            
            for row in rows:
                id_g = int(row[0])
                if id_g in mapa_jerarquia:
                    fam, nombre_bonito = mapa_jerarquia[id_g]
                    subfam = nombre_bonito
                else:
                    fam = "OTRAS"
                    subfam = row[1] or "Desconocido"

                objs.append(OportunidadEFP(
                    farmacia_id=farmacia_id,
                    id_agrupacion=int(row[0]),
                    nombre_grupo=subfam,
                    familia=fam,
                    subfamilia=subfam,
                    producto_recomendado=row[2],
                    pvp_medio=float(row[3] or 0),
                    margen_pct=float(row[4] or 0),
                    ahorro_potencial=float(row[5] or 0),
                    a_sustituir=row[6] or "",
                    codigo_nacional=str(row[7]) if row[7] else ""
                ))
            OportunidadEFP.objects.bulk_create(objs)
            
        return len(objs), None

    except Exception as e:
        return 0, str(e)
    
def generar_pregunta_examen(farmacia_id):
    """
    Genera una pregunta donde TODAS las opciones pertenecen al MISMO grupo terapéutico.
    Devuelve lista de OBJETOS (dicts) con nombre, cn y pvp.
    """
    # 1. Buscamos grupos que tengan competencia
    qs = OportunidadEFP.objects.filter(farmacia_id=farmacia_id).exclude(a_sustituir="")
    items_posibles = list(qs)
    
    if not items_posibles: return None

    random.shuffle(items_posibles)

    # 2. Iteramos para encontrar un grupo válido
    for item in items_posibles:
        # --- GANADOR ---
        ganador = {
            'nombre': item.producto_recomendado, 
            'cn': item.codigo_nacional,
            'pvp': float(item.pvp_medio) if item.pvp_medio else 0.0
        }
        
        # --- COMPETIDORES (Parseo Robusto) ---
        raw_competidores = item.a_sustituir.split(' || ')
        distractores_objs = []
        
        for raw in raw_competidores:
            # Intentamos parsear: "Nombre (Unidades###Margen###Cuota###CN)"
            # Usamos rpartition para separar desde el último parentesis
            nombre_part, separador, datos_part = raw.rpartition(' (')
            
            if separador:
                datos_limpios = datos_part.rstrip(')')
                parts = datos_limpios.split('###')
                
                cn_comp = ""
                pvp_comp = 0.0
                
                if len(parts) >= 5:
                    cn_comp = parts[3]
                    try:
                        pvp_comp = float(parts[4])
                    except:
                        pvp_comp = 0.0
                elif len(parts) == 4: # Backwards compatibility
                    cn_comp = parts[3]

                nombre_final = nombre_part.strip()
                
                if nombre_final and nombre_final != ganador['nombre']:
                    distractores_objs.append({
                        'nombre': nombre_final, 
                        'cn': cn_comp, 
                        'pvp': pvp_comp # Now we have it!
                    })
        
        # Filtrar duplicados por nombre
        # (Usamos un dict intermedio para unicidad)
        unique_distractores = {d['nombre']: d for d in distractores_objs}.values()
        distractores_finales = list(unique_distractores)

        # 3. Validar si tenemos suficientes opciones
        # Intentamos conseguir 2 distractores
        if len(distractores_finales) >= 1:
            # Si hay 2 o más, cogemos 2. Si hay 1, cogemos 1.
            count_to_take = min(len(distractores_finales), 2)
            seleccion = random.sample(distractores_finales, count_to_take)
            
            opciones = [ganador] + seleccion
            random.shuffle(opciones)
            
            return {
                'id_pregunta': str(item.id),
                'pregunta_texto': item.nombre_grupo,
                'producto_correcto': ganador['nombre'],
                'opciones': opciones, # Lista de diccionarios
                'explicacion': f"**{ganador['nombre']}** es la opción recomendada por rentabilidad en este grupo."
            }

    return None
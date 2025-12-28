import os
from django.db import transaction
from .models import Oportunidad
from .db_utils import databricks_connection, bulk_create_or_update, get_farmacias_activas, parse_percentage_string, parse_currency_string
from dotenv import load_dotenv

load_dotenv()

def sincronizar_desde_databricks(farmacia_id, fecha_inicio, fecha_fin):
    """
    Sincroniza oportunidades de AH desde Databricks para una farmacia específica.
    
    Args:
        farmacia_id (str): ID de la farmacia
        fecha_inicio (str): Fecha inicio en formato 'YYYY-MM-DD'
        fecha_fin (str): Fecha fin en formato 'YYYY-MM-DD'
    
    Returns:
        tuple: (num_registros, error_message)
    """
    try:
        query = f"""
        WITH Base AS (
            SELECT 
                bd.IdArticu,
                MAX(pmf.Nombre_Producto) as Nombre_Completo,
                MAX(pmf.Nombre_Producto) as Nombre_Largo, 
                MAX(pmf.Principio_Activo) as Principio_Activo,
                MAX(CAST(regexp_replace(pmf.Codigo_Agrupacion, ',', '.') AS DOUBLE)) as Id_Agrupacion,
                SUM(bd.Cantidad) as Unidades,
                SUM(bd.ImporteBruto) as Venta_Total,
                
                (SUM(bd.ImporteBruto) / NULLIF(SUM(bd.Cantidad),0)) as PVP_Medio_Real,
                (SUM(COALESCE(bd.ImporteCoste, 0)) / NULLIF(SUM(bd.Cantidad),0)) as PUC_Medio_Real,
                ((SUM(bd.ImporteBruto) - SUM(COALESCE(bd.ImporteCoste, 0))) / NULLIF(SUM(bd.Cantidad),0)) as Margen_Unit_Eur,
                
                CASE WHEN SUM(bd.ImporteBruto) > 0 THEN
                    ((SUM(bd.ImporteBruto) - SUM(COALESCE(bd.ImporteCoste, 0))) / SUM(bd.ImporteBruto)) * 100
                ELSE 0 END as Margen_Pct
                
            FROM cat_farma.datavaultperformance.bridge_dispensacion bd
            INNER JOIN cat_farma.datavaultperformance.pip_medicamentos_financiados pmf
                ON CAST(bd.IdArticu AS STRING) = CAST(pmf.Codigo_Nacional AS STRING)
            
            WHERE bd.fecha >= DATE '{fecha_inicio}' AND bd.fecha <= DATE '{fecha_fin}'
              AND bd.FARMACIA_NOM = '{farmacia_id}'
              AND pmf.Codigo_Agrupacion IS NOT NULL
              AND pmf.Estado = 'ALTA'
            
            GROUP BY bd.IdArticu
            HAVING SUM(bd.Cantidad) > 0 AND SUM(COALESCE(bd.ImporteCoste, 0)) > 0
        ),
        Ranked AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (PARTITION BY Id_Agrupacion ORDER BY Margen_Unit_Eur DESC) as Ranking,
                MAX(Margen_Unit_Eur) OVER (PARTITION BY Id_Agrupacion) as Mejor_Margen_Eur
            FROM Base
        )
        SELECT 
            MAX(Principio_Activo) as Grupo,
            MAX(CASE WHEN Ranking = 1 THEN Nombre_Largo END) as Campeon,
            MAX(CASE WHEN Ranking = 1 THEN PVP_Medio_Real END) as PVP,
            MAX(CASE WHEN Ranking = 1 THEN PUC_Medio_Real END) as PUC,
            concat(format_number(MAX(CASE WHEN Ranking = 1 THEN Margen_Pct END), 2), '%'),
            concat(format_number((MAX(CASE WHEN Ranking = 1 THEN Unidades END) / SUM(Unidades)) * 100, 1), '%'),
            
            array_join(collect_list(
                CASE 
                    WHEN Ranking > 1 
                    THEN concat(Nombre_Largo, ' (', CAST(Unidades AS INT), '|', CAST(ROUND(Margen_Pct, 0) AS INT), '%|', IdArticu, ')') 
                END
            ), ' || '),
            
            SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)) as Ahorro_Calculado,
            MAX(CASE WHEN Ranking = 1 THEN IdArticu END) as CN_Recomendado
        FROM Ranked
        GROUP BY Id_Agrupacion
        HAVING SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)) > 10
        ORDER BY SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)) DESC
        """
        
        with databricks_connection() as (connection, cursor):
            cursor.execute(query)
            rows = cursor.fetchall()
        
        # Procesar y crear objetos
        objs = []
        for row in rows:
            margen_clean = parse_percentage_string(row[4])
            penet_clean = parse_percentage_string(row[5])
            ahorro_clean = parse_currency_string(row[7])
            cn_clean = str(row[8]) if row[8] else ""
            
            objs.append(Oportunidad(
                farmacia_id=farmacia_id,
                grupo_homogeneo=row[0],
                producto_recomendado=row[1],
                pvp_medio=float(row[2]),
                puc_medio=float(row[3]),
                margen_pct=margen_clean,
                penetracion_pct=penet_clean,
                a_sustituir=row[6],
                ahorro_potencial=ahorro_clean,
                codigo_nacional=cn_clean
            ))
        
        num_created = bulk_create_or_update(Oportunidad, farmacia_id, objs)
        return num_created, None

    except Exception as e:
        return 0, str(e)
    
def obtener_farmacias_cloud():
    """
    Obtiene la lista de farmacias ACTIVAS desde la tabla maestra de Databricks.
    
    Esta es un wrapper de la función genérica en db_utils para mantener compatibilidad.
    
    Returns:
        tuple: (lista_farmacias, error_message)
    """
    return get_farmacias_activas()
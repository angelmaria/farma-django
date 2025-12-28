import os
from databricks import sql
from django.db import transaction
from .models import Oportunidad
from dotenv import load_dotenv

load_dotenv()

def sincronizar_desde_databricks(farmacia_id, fecha_inicio, fecha_fin):
    try:
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        cursor = connection.cursor()

        # QUERY: Añadimos IdArticu (CN) al string de competidores
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
            
            -- AQUÍ ESTÁ EL CAMBIO: Añadimos '|' y IdArticu al final
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
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cursor.close()
        connection.close()

        with transaction.atomic():
            Oportunidad.objects.filter(farmacia_id=farmacia_id).delete()
            objs = []
            for row in rows:
                margen_clean = float(row[4].replace('%', '')) if row[4] else 0
                penet_clean = float(row[5].replace('%', '')) if row[5] else 0
                ahorro_clean = float(str(row[7]).replace(',', '')) if row[7] else 0
                # CN is at index 8
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
                    codigo_nacional=cn_clean # Map the new CN column
                ))
            Oportunidad.objects.bulk_create(objs)
            
        return len(objs), None

    except Exception as e:
        return 0, str(e)
    
def obtener_farmacias_cloud():
    """
    Obtiene la lista de farmacias ACTIVAS desde la tabla maestra de Databricks.
    """
    try:
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        cursor = connection.cursor()
        
        # Consultamos la tabla maestra 'nom_farmacias'
        # Filtramos por ACTIVO = 1 para traer solo las operativas
        query = """
            SELECT FARMACIA_NOM 
            FROM cat_farma.datavaultperformance.nom_farmacias 
            WHERE ACTIVO = 1 
            ORDER BY FARMACIA_NOM
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Convertimos la lista de tuplas [('HF...'), ...] en lista simple ['HF...', ...]
        lista = [row[0] for row in rows]
        return lista, None
        
    except Exception as e:
        print(f"ERROR DATABRICKS (Farmacias): {str(e)}")
        return [], str(e)
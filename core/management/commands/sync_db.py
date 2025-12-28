import os
from django.core.management.base import BaseCommand
from core.models import Oportunidad
from databricks import sql
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Sincroniza datos desde Databricks'

    def add_arguments(self, parser):
        parser.add_argument('--farmacia_id', type=str, help='ID de la farmacia a sincronizar')

    def handle(self, *args, **kwargs):
        self.stdout.write("Conectando a Databricks...")
        
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )

        cursor = connection.cursor()
        
        # TU QUERY SPARK AQUÍ (Copia la query query_producto_completo_fix exacta)
        query = """
        WITH Base AS (
    SELECT 
        bd.IdArticu,
        MAX(pmf.Nombre_Producto) as Nombre_Completo,
        MAX(pmf.Nombre_Producto) as Nombre_Largo, 
        MAX(pmf.Principio_Activo) as Principio_Activo,
        MAX(CAST(regexp_replace(pmf.Codigo_Agrupacion, ',', '.') AS DOUBLE)) as Id_Agrupacion,
        SUM(bd.Cantidad) as Unidades,
        SUM(bd.ImporteBruto) as Venta_Total,
        
        -- CÁLCULOS DE PRECIOS
        (SUM(bd.ImporteBruto) / NULLIF(SUM(bd.Cantidad),0)) as PVP_Medio_Real,
        (SUM(COALESCE(bd.ImporteCoste, 0)) / NULLIF(SUM(bd.Cantidad),0)) as PUC_Medio_Real,
        
        -- Margen Unitario Absoluto
        ((SUM(bd.ImporteBruto) - SUM(COALESCE(bd.ImporteCoste, 0))) / NULLIF(SUM(bd.Cantidad),0)) as Margen_Unit_Eur,
        
        -- Margen %
        CASE WHEN SUM(bd.ImporteBruto) > 0 THEN
            ((SUM(bd.ImporteBruto) - SUM(COALESCE(bd.ImporteCoste, 0))) / SUM(bd.ImporteBruto)) * 100
        ELSE 0 END as Margen_Pct
        
    FROM cat_farma.datavaultperformance.bridge_dispensacion bd
    INNER JOIN cat_farma.datavaultperformance.pip_medicamentos_financiados pmf
        ON CAST(bd.IdArticu AS STRING) = CAST(pmf.Codigo_Nacional AS STRING)
    WHERE bd.fecha >= DATE '2024-01-01' AND bd.fecha < DATE '2025-01-01'
      AND bd.FARMACIA_NOM = 'HF280050001'
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
    MAX(Principio_Activo) as Grupo,      -- row[0]
    MAX(CASE WHEN Ranking = 1 THEN Nombre_Largo END) as Campeon, -- row[1]
    MAX(CASE WHEN Ranking = 1 THEN PVP_Medio_Real END) as PVP,   -- row[2]
    MAX(CASE WHEN Ranking = 1 THEN PUC_Medio_Real END) as PUC,   -- row[3]
    concat(format_number(MAX(CASE WHEN Ranking = 1 THEN Margen_Pct END), 2), '%') as Margen_Texto, -- row[4]
    concat(format_number((MAX(CASE WHEN Ranking = 1 THEN Unidades END) / SUM(Unidades)) * 100, 1), '%') as Penetracion_Texto, -- row[5]
    array_join(collect_list(
        CASE 
            WHEN Ranking > 1 
            THEN concat(substr(Nombre_Largo, 1, 40), '...(', CAST(Unidades AS INT), '|', CAST(ROUND(Margen_Pct, 0) AS INT), '%)') 
        END
    ), ' || ') as Lista_Evitar, -- row[6]
    SUM(Unidades * (Mejor_Margen_Eur - Margen_Unit_Eur)) as Ahorro_Total_Eur -- row[7]

FROM Ranked
GROUP BY Id_Agrupacion
HAVING Ahorro_Total_Eur > 10
ORDER BY Ahorro_Total_Eur DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()

        self.stdout.write(f"Descargados {len(rows)} registros. Guardando en Django...")

        # Transacción atómica para seguridad
        from django.db import transaction
        with transaction.atomic():
            Oportunidad.objects.all().delete() # Limpieza total (o usa update logic)
            
            objs = []
            for row in rows:
                # Mapeo de columnas (Ajusta los índices según tu SELECT final)
                # Select: 0:Grupo, 1:Campeon, 2:PVP, 3:PUC, 4:Margen, 5:Penet, 6:Lista, 7:Ahorro
                
                # Limpieza de strings que vienen formateados (ej: "77.61%")
                margen_clean = float(row[4].replace('%', '')) if row[4] else 0
                penet_clean = float(row[5].replace('%', '')) if row[5] else 0
                ahorro_clean = float(str(row[7]).replace(',', '')) if row[7] else 0
                
                objs.append(Oportunidad(
                    grupo_homogeneo=row[0],
                    producto_recomendado=row[1],
                    pvp_medio=float(row[2]),
                    puc_medio=float(row[3]),
                    margen_pct=margen_clean,
                    penetracion_pct=penet_clean,
                    a_sustituir=row[6],
                    ahorro_potencial=ahorro_clean
                ))
            
            Oportunidad.objects.bulk_create(objs)

        cursor.close()
        connection.close()
        self.stdout.write(self.style.SUCCESS('Sincronización completada.'))

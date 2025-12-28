# core/db_utils.py
"""
Utilidades compartidas para operaciones con Databricks y base de datos.
"""
import os
from contextlib import contextmanager
from databricks import sql
from django.db import transaction
from dotenv import load_dotenv

load_dotenv()


@contextmanager
def databricks_connection():
    """
    Context manager para manejar conexiones a Databricks de forma segura.
    
    Uso:
        with databricks_connection() as (connection, cursor):
            cursor.execute("SELECT * FROM tabla")
            results = cursor.fetchall()
    
    Garantiza que la conexión y cursor se cierren siempre, incluso si hay errores.
    """
    connection = None
    cursor = None
    try:
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        cursor = connection.cursor()
        yield connection, cursor
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def execute_databricks_query(query, farmacia_id=None):
    """
    Ejecuta una consulta en Databricks y devuelve los resultados.
    
    Args:
        query (str): Query SQL a ejecutar
        farmacia_id (str, optional): ID de farmacia para reemplazar en la query
    
    Returns:
        tuple: (rows, error)
            - rows: Lista de resultados si tiene éxito
            - error: String con mensaje de error si falla, None en caso contrario
    """
    try:
        # Si se proporciona farmacia_id, reemplazar placeholder
        if farmacia_id:
            query = query.replace('{farmacia_id}', farmacia_id)
        
        with databricks_connection() as (connection, cursor):
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows, None
    except Exception as e:
        return [], str(e)


def bulk_create_or_update(model_class, farmacia_id, objects_list, delete_existing=True):
    """
    Crea o actualiza objetos en masa de forma atómica.
    
    Args:
        model_class: Clase del modelo Django (ej: Oportunidad)
        farmacia_id (str): ID de la farmacia
        objects_list (list): Lista de instancias del modelo a crear
        delete_existing (bool): Si True, elimina registros existentes antes de insertar
    
    Returns:
        int: Número de objetos creados
    """
    with transaction.atomic():
        if delete_existing:
            model_class.objects.filter(farmacia_id=farmacia_id).delete()
        
        if objects_list:
            model_class.objects.bulk_create(objects_list)
        
        return len(objects_list)


def get_farmacias_activas():
    """
    Obtiene la lista de farmacias activas desde Databricks.
    
    Returns:
        tuple: (lista_farmacias, error)
            - lista_farmacias: Lista de IDs de farmacias activas
            - error: String con mensaje de error o None
    """
    query = """
        SELECT FARMACIA_NOM 
        FROM cat_farma.datavaultperformance.nom_farmacias 
        WHERE ACTIVO = 1 
        ORDER BY FARMACIA_NOM
    """
    
    try:
        with databricks_connection() as (connection, cursor):
            cursor.execute(query)
            rows = cursor.fetchall()
            lista = [row[0] for row in rows]
            return lista, None
    except Exception as e:
        return [], str(e)


def parse_percentage_string(value):
    """
    Convierte un string con porcentaje a float.
    
    Args:
        value: String como "77.61%" o número
    
    Returns:
        float: Valor numérico sin el símbolo %
    """
    if value is None:
        return 0.0
    
    if isinstance(value, str):
        return float(value.replace('%', '').replace(',', ''))
    
    return float(value)


def parse_currency_string(value):
    """
    Convierte un string con formato de moneda a float.
    
    Args:
        value: String como "1,234.56" o número
    
    Returns:
        float: Valor numérico
    """
    if value is None:
        return 0.0
    
    if isinstance(value, str):
        return float(value.replace(',', ''))
    
    return float(value)

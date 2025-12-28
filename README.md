# 💊 FarmaSwitch - Sistema de Optimización de Márgenes Farmacéuticos

Sistema web Django diseñado para maximizar la rentabilidad de farmacias mediante análisis inteligente de márgenes y recomendaciones de sustitución terapéutica.

## 📋 Descripción

FarmaSwitch identifica oportunidades de mejora analizando dos segmentos clave:

- **Análisis Homogéneo (AH)**: Medicamentos financiados con el mismo principio activo
- **Especialidades Farmacéuticas Publicitarias (EFP)**: Medicamentos de venta libre

El sistema se conecta a Databricks para obtener datos de dispensación y calcula automáticamente qué productos ofrecen mejor margen dentro de cada grupo terapéutico.

## ✨ Características Principales

### 📊 Dashboard Inteligente
- **KPIs en tiempo real**: Ahorro potencial total y mensual
- **Top 5 oportunidades**: Ordenadas por impacto económico
- **Filtros por familia**: Sistema respiratorio, digestivo, dermatología, etc.
- **Selector de farmacia**: Cambio rápido entre diferentes puntos de venta (para administradores)

### 🔍 Buscador Avanzado
- Búsqueda por principio activo, nombre comercial o laboratorio
- Resultados filtrados por farmacia activa
- Detalles de márgenes y alternativas disponibles

### 📈 Datos Brutos
- Tabla completa de todas las oportunidades detectadas
- Ordenación por múltiples criterios (ahorro, margen, penetración)
- Exportable para análisis externos

### 🎓 Módulo de Entrenamiento
- **Gimnasio Virtual**: Práctica ilimitada con casos reales
- Aprende qué producto recomendar en cada situación
- Sistema de preferencias personalizado

### 🎯 Examen de Conocimientos
- 10 preguntas aleatorias del catálogo real
- Feedback instantáneo con explicaciones
- Puntuación final y recomendaciones de mejora

### ⚙️ Configuración Personalizada
- Establece preferencias por laboratorio
- Override del algoritmo automático
- Gestión por grupo homogéneo

## 🛠️ Tecnologías

- **Backend**: Django 5.2.9
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL recomendado (producción)
- **Data Source**: Databricks SQL Warehouse
- **Despliegue**: Gunicorn + Whitenoise
- **Frontend**: Bootstrap 5 + Font Awesome

## 📦 Instalación

### Requisitos Previos
- Python 3.11+
- Acceso a Databricks (credenciales requeridas)

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/angelmaria/farma-django.git
cd farma-django
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Crear archivo `.env` en la raíz del proyecto:
```env
SECRET_KEY=tu-secret-key-segura-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Databricks
DATABRICKS_SERVER_HOSTNAME=tu-servidor.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/xxxxx
DATABRICKS_TOKEN=dapi...
```

5. **Migrar base de datos**
```bash
python manage.py migrate
```

6. **Crear superusuario**
```bash
python manage.py createsuperuser
```

7. **Sincronizar datos desde Databricks**
```bash
# Importar desde la interfaz web (Dashboard > Importar)
# O usar el comando de gestión:
python manage.py sync_db --farmacia_id HF280050001
```

8. **Ejecutar servidor de desarrollo**
```bash
python manage.py runserver
```

Accede a: http://127.0.0.1:8000

## 🚀 Despliegue en VPS

### Con Gunicorn + Nginx

1. **Configurar settings para producción**
```python
DEBUG = False
ALLOWED_HOSTS = ['tu-dominio.com', 'www.tu-dominio.com']
```

2. **Recolectar archivos estáticos**
```bash
python manage.py collectstatic --noinput
```

3. **Ejecutar con Gunicorn**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

4. **Configurar Nginx** (opcional, para SSL y caché)
```nginx
server {
    listen 80;
    server_name tu-dominio.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /ruta/a/staticfiles/;
    }
}
```

## 📂 Estructura del Proyecto

```
farma-django/
├── config/              # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                # App Análisis Homogéneo (AH)
│   ├── models.py        # Oportunidad, Preferencia, PerfilFarmacia
│   ├── views.py         # Dashboard, Buscador, Entrenamiento...
│   ├── services.py      # Conexión Databricks
│   ├── templates/       # HTML templates
│   └── management/      # Comandos personalizados
├── efp/                 # App EFP (Venta Libre)
│   ├── models.py        # OportunidadEFP, PreferenciaEFP
│   ├── views.py
│   ├── services.py
│   ├── data/            # JSON de categorización
│   └── templates/
├── media/               # Imágenes de productos
├── requirements.txt     # Dependencias Python
├── pyproject.toml       # Configuración uv/pip
├── manage.py
└── db.sqlite3          # Base de datos local
```

## 🔐 Gestión de Usuarios

### Tipos de Usuario

1. **Superusuario/Staff**: Acceso completo, puede cambiar entre farmacias
2. **Usuario Farmacia**: Vinculado a una farmacia específica mediante `PerfilFarmacia`

### Asignar Farmacia a Usuario

```python
from django.contrib.auth.models import User
from core.models import PerfilFarmacia

user = User.objects.get(username='nombre_usuario')
PerfilFarmacia.objects.create(user=user, farmacia_id='HF280050001')
```

## 📊 Modelo de Datos

### Oportunidad (AH)
- `grupo_homogeneo`: Principio activo
- `producto_recomendado`: Opción más rentable
- `pvp_medio` / `puc_medio`: Precios
- `margen_pct`: Porcentaje de margen
- `penetracion_pct`: Cuota de mercado actual
- `a_sustituir`: Competidores a reemplazar
- `ahorro_potencial`: Impacto económico anual

### OportunidadEFP
- Similar a Oportunidad, específico para venta libre
- `familia` / `subfamilia`: Categorización terapéutica
- `id_agrupacion`: ID del grupo EFP

## 🧪 Comandos de Gestión

```bash
# Sincronizar datos desde Databricks
python manage.py sync_db --farmacia_id HF280050001

# Cargar datos de ejemplo (desarrollo)
python manage.py cargar_datos

# Descargar imágenes de productos EFP
python manage.py descargar_fotos_efp
```

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Añade nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Documentación Adicional

- [Manual del Proyecto](MANUAL_PROYECTO.md) - Documentación técnica completa
- [Script Corrector Automático](corrector_automatico.py) - Herramienta de análisis de código

## 🐛 Problemas Conocidos

- El modelo `Preferencia` necesita campo `farmacia_id` para multitenancy completo (ver `corrector_automatico.py`)
- Las consultas a Databricks pueden tardar en entornos con latencia alta

## 📄 Licencia

Este proyecto es propiedad privada. Todos los derechos reservados.

## 👤 Autor

**Ángel María**
- GitHub: [@angelmaria](https://github.com/angelmaria)

## 🙏 Agradecimientos

- Novaquality por los requisitos y especificaciones del proyecto
- Databricks por la infraestructura de datos
- Comunidad Django por las herramientas y documentación

---

**Versión**: 0.1.0  
**Última actualización**: Diciembre 2025

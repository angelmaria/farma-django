# 📚 MANUAL COMPLETO DEL PROYECTO FARMA_DJANGO

## 🎯 ¿QUÉ ES ESTE PROYECTO?

**farma_django** es una aplicación web que ayuda a farmacias a **maximizar sus márgenes de beneficio** identificando oportunidades de cambio de productos. La aplicación analiza el stock actual y sugiere sustituciones inteligentes que mantienen la misma eficacia pero aumentan el margen de ganancia.

---

## 📁 ESTRUCTURA DEL PROYECTO

```
farma_django/
│
├── manage.py              # 🔧 Comando principal de Django
├── .env                   # 🔐 Variables secretas (contraseñas, keys)
├── db.sqlite3             # 💾 Base de datos local
├── requirements.txt       # 📦 Lista de dependencias
│
├── config/                # ⚙️ Configuración general del proyecto
│   ├── settings.py        # Configuración principal
│   ├── urls.py            # Rutas principales
│   └── wsgi.py            # Servidor web
│
├── core/                  # 🏥 App principal (Agrupaciones Homogéneas)
│   ├── models.py          # Estructura de datos
│   ├── views.py           # Lógica de las páginas
│   ├── urls.py            # Rutas de core
│   ├── services.py        # Conexión con Databricks
│   ├── forms.py           # Formularios
│   ├── admin.py           # Panel de administración
│   ├── templates/         # Plantillas HTML
│   └── management/        # Comandos personalizados
│
└── efp/                   # 💊 App secundaria (EFP - Especialidades Farmacéuticas)
    ├── models.py          # Estructura de datos EFP
    ├── views.py           # Lógica de páginas EFP
    ├── urls.py            # Rutas de EFP
    ├── services.py        # Conexión con Databricks EFP
    └── templates/         # Plantillas HTML EFP
```

---

## 🚀 NIVEL 1: ARCHIVOS DE INICIO

### 1️⃣ `manage.py` - El Director de Orquesta

```python
#!/usr/bin/env python
import os
import sys
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env
```

**¿Qué hace?**
- Es el **punto de entrada** de toda la aplicación
- Carga las **variables de entorno** del archivo `.env` (contraseñas, claves secretas)
- Permite ejecutar comandos como:
  - `python manage.py runserver` → Inicia el servidor
  - `python manage.py migrate` → Actualiza la base de datos
  - `python manage.py createsuperuser` → Crea un usuario administrador

**Analogía:** Es como el director de orquesta que coordina todos los músicos (módulos).

---

### 2️⃣ `.env` - La Caja Fuerte de Secretos

```
SECRET_KEY=tu_clave_secreta_aqui
DATABRICKS_TOKEN=tu_token_aqui
DEBUG=True
```

**¿Qué hace?**
- Guarda información **sensible** que NO debe subirse a GitHub
- Contiene:
  - `SECRET_KEY`: Clave de seguridad de Django
  - `DATABRICKS_TOKEN`: Contraseña para acceder a la base de datos en la nube
  - `DEBUG`: Modo desarrollo (muestra errores detallados)

**Analogía:** Es tu caja fuerte donde guardas contraseñas y claves.

---

### 3️⃣ `requirements.txt` - La Lista de la Compra

```
Django==5.2.9
python-dotenv==1.0.0
databricks-sql-connector==3.0.0
whitenoise==6.5.0
```

**¿Qué hace?**
- Lista todas las **librerías externas** que necesita el proyecto
- Se instalan con: `pip install -r requirements.txt`

**Analogía:** Es la lista de ingredientes que necesitas comprar antes de cocinar.

---

## ⚙️ NIVEL 2: CONFIGURACIÓN (carpeta `config/`)

### 1️⃣ `config/settings.py` - El Cerebro del Proyecto

Este archivo configura **TODA** la aplicación. Vamos por partes:

#### 🔐 Seguridad
```python
SECRET_KEY = os.environ["SECRET_KEY"]  # Lee la clave del .env
DEBUG = True  # Muestra errores en desarrollo
ALLOWED_HOSTS = []  # Dominios permitidos (vacío en desarrollo)
```

#### 📦 Aplicaciones Instaladas
```python
INSTALLED_APPS = [
    'django.contrib.admin',      # Panel de administración
    'django.contrib.auth',       # Sistema de usuarios
    'django.contrib.sessions',   # Manejo de sesiones (login)
    'django.contrib.messages',   # Mensajes flash
    'core',                      # ⭐ Nuestra app principal
    'efp',                       # ⭐ Nuestra app de EFP
    'django.contrib.humanize',   # Formateo de números (1000 → 1,000)
]
```

**¿Qué hace cada una?**
- `admin`: Te permite gestionar datos desde un panel web
- `auth`: Gestiona usuarios, login, permisos
- `sessions`: Recuerda quién está conectado
- `messages`: Muestra notificaciones ("Datos guardados correctamente")
- `core` y `efp`: **Tus aplicaciones personalizadas**
- `humanize`: Hace los números más legibles

#### 🔧 Middleware (Intermediarios)
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Sirve archivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',  # Gestiona sesiones
    'django.middleware.csrf.CsrfViewMiddleware',  # Protección contra ataques
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Identifica usuarios
]
```

**Analogía:** Los middleware son como **filtros de seguridad** en un aeropuerto. Cada petición pasa por ellos antes de llegar a tu código.

#### 💾 Base de Datos
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # Archivo local
    }
}
```

**¿Qué hace?**
- Define que usas **SQLite** (base de datos ligera en un archivo)
- El archivo `db.sqlite3` contiene todas las tablas

#### 🌍 Internacionalización
```python
LANGUAGE_CODE = 'es-es'  # Español
TIME_ZONE = 'Europe/Madrid'  # Zona horaria
USE_I18N = True  # Activa traducciones
```

#### 📁 Archivos Estáticos (CSS, JS, Imágenes)
```python
STATIC_URL = '/static/'  # URL base para CSS/JS
STATICFILES_DIRS = [BASE_DIR / "static"]  # Carpeta de archivos estáticos
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para producción

MEDIA_URL = '/media/'  # URL para imágenes subidas
MEDIA_ROOT = BASE_DIR / 'media'  # Carpeta de imágenes
```

---

### 2️⃣ `config/urls.py` - El Mapa de Rutas

```python
urlpatterns = [
    path('admin/', admin.site.urls),  # /admin → Panel de administración
    path('efp/', include('efp.urls')),  # /efp → App de EFP
    path('', include('core.urls')),  # / → App principal
]
```

**¿Qué hace?**
- Define **qué URL lleva a qué página**
- Ejemplo:
  - `http://localhost:8000/admin/` → Panel de administración
  - `http://localhost:8000/efp/` → Dashboard de EFP
  - `http://localhost:8000/` → Dashboard principal

**Analogía:** Es el mapa de un centro comercial que dice "Ropa → Piso 1, Comida → Piso 2".

---

## 🏥 NIVEL 3: APP PRINCIPAL (`core/`)

### 1️⃣ `core/models.py` - La Estructura de Datos

Los **modelos** definen **qué información guardamos** y **cómo se organiza**.

#### 📋 Modelo: `PerfilFarmacia`
```python
class PerfilFarmacia(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    farmacia_id = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.user.username} - {self.farmacia_id}"
```

**¿Qué hace?**
- **Extiende** el usuario de Django con información adicional
- Cada usuario tiene **UNA** farmacia asociada
- `farmacia_id`: Identificador único (ej: "HF280050001")

**Analogía:** Es como un **badge de empleado** que asocia a una persona con su tienda.

---

#### 💊 Modelo: `Oportunidad` (El más importante)
```python
class Oportunidad(models.Model):
    grupo_homogeneo = models.CharField(max_length=255)  # Ej: "OMEPRAZOL 20MG"
    producto_recomendado = models.CharField(max_length=255)  # Ej: "OMEPRAZOL CINFA"
    pvp_medio = models.DecimalField(max_digits=10, decimal_places=2)  # Precio venta
    puc_medio = models.DecimalField(max_digits=10, decimal_places=2)  # Precio coste
    margen_pct = models.DecimalField(max_digits=5, decimal_places=2)  # % de margen
    penetracion_pct = models.DecimalField(max_digits=5, decimal_places=2)  # % de cuota
    a_sustituir = models.TextField()  # Lista de competidores
    ahorro_potencial = models.DecimalField(max_digits=10, decimal_places=2)  # € ahorro
    farmacia_id = models.CharField(max_length=50)  # ID de la farmacia
```

**¿Qué guarda cada campo?**
- `grupo_homogeneo`: Categoría del medicamento (principio activo + dosis)
- `producto_recomendado`: El producto que deberías vender
- `pvp_medio`: Precio de Venta al Público promedio
- `puc_medio`: Precio Unitario de Coste promedio
- `margen_pct`: **% de ganancia** (pvp - puc)
- `penetracion_pct`: **% de cuota de mercado** que tienes
- `a_sustituir`: String con competidores a evitar
- `ahorro_potencial`: **€ que ganarías** si cambias
- `farmacia_id`: ¿De qué farmacia es esta oportunidad?

**Ejemplo de registro:**
```
grupo_homogeneo: "IBUPROFENO 600MG"
producto_recomendado: "IBUPROFENO NORMON"
pvp_medio: 2.50€
puc_medio: 0.80€
margen_pct: 68%
penetracion_pct: 35%
a_sustituir: "NEOBRUFEN (1200|45%%) || ESPIDIFEN (800|38%%)"
ahorro_potencial: 450€
farmacia_id: "HF280050001"
```

---

#### 🔍 Método: `get_competidores_stats()`
```python
def get_competidores_stats(self):
    """
    Parsea el string 'Marca (Unidades|Margen%) || Marca2 (Unidades|Margen%)'
    y devuelve una lista de diccionarios con % calculado.
    """
```

**¿Qué hace?**
1. Toma el campo `a_sustituir` (que es un string)
2. Lo **descompone** en una lista de competidores
3. Calcula el **% de penetración** de cada uno
4. Devuelve una lista de diccionarios

**Ejemplo de entrada:**
```
"NEOBRUFEN (1200|45%) || ESPIDIFEN (800|38%)"
```

**Ejemplo de salida:**
```python
[
    {'nombre': '🏆 IBUPROFENO NORMON', 'penet': 35.0, 'margen': 68, 'es_campeon': True},
    {'nombre': 'NEOBRUFEN', 'penet': 42.0, 'margen': 45, 'es_campeon': False},
    {'nombre': 'ESPIDIFEN', 'penet': 23.0, 'margen': 38, 'es_campeon': False}
]
```

**¿Por qué es útil?**
- El HTML puede iterar sobre esta lista para mostrar barras de progreso
- Cada competidor tiene su % de penetración calculado

---

#### 🎯 Modelo: `Preferencia`
```python
class Preferencia(models.Model):
    grupo_homogeneo = models.CharField(max_length=255, unique=True)
    laboratorio_preferente = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    farmacia_id = models.CharField(max_length=50)
```

**¿Qué hace?**
- Permite al farmacéutico **sobreescribir** la recomendación del algoritmo
- Si el farmacéutico prefiere un laboratorio específico, se guarda aquí

**Ejemplo:**
```
grupo_homogeneo: "IBUPROFENO 600MG"
laboratorio_preferente: "KERN PHARMA"  ← Elección manual
activo: True
farmacia_id: "HF280050001"
```

---

### 2️⃣ `core/views.py` - La Lógica de las Páginas

Las **vistas** son funciones que:
1. Reciben una petición del navegador
2. Consultan la base de datos
3. Devuelven una página HTML

Vamos a analizar las principales:

---

#### 🏠 Vista: `dashboard()`
```python
@login_required(login_url='login')
def dashboard(request):
```

**¿Qué hace?**
1. **Verifica** que el usuario esté logueado
2. Obtiene la farmacia activa del usuario
3. Filtra las oportunidades de esa farmacia
4. Calcula KPIs (ahorro total, número de grupos, etc.)
5. Selecciona las **Top 5 oportunidades** con más ahorro
6. Renderiza el template `dashboard.html`

**Flujo paso a paso:**
```python
# 1. Obtener farmacia del usuario
farmacia_activa = request.session.get('farmacia_activa')

# 2. Filtrar datos
oportunidades = Oportunidad.objects.filter(farmacia_id=farmacia_activa)

# 3. Calcular KPIs
total_ahorro = oportunidades.aggregate(Sum('ahorro_potencial'))
total_grupos = oportunidades.count()

# 4. Top 5
top_5 = oportunidades.order_by('-ahorro_potencial')[:5]

# 5. Renderizar HTML
return render(request, 'core/dashboard.html', {
    'top_5': top_5,
    'total_ahorro': total_ahorro,
    'total_grupos': total_grupos,
})
```

---

#### 📊 Vista: `oportunidades()`
```python
def oportunidades(request):
    # Muestra TODAS las oportunidades en una tabla
```

**¿Qué hace?**
1. Obtiene todas las oportunidades de la farmacia
2. Aplica **filtros** (búsqueda, margen mínimo)
3. **Ordena** por ahorro descendente
4. Aplica **paginación** (20 por página)
5. Renderiza `oportunidades.html`

---

#### ⚙️ Vista: `configuracion()`
```python
def configuracion(request):
    # Permite al farmacéutico elegir laboratorios preferidos
```

**¿Qué hace?**
1. Muestra todas las oportunidades
2. Para cada una, muestra:
   - Recomendación del algoritmo
   - Lista de competidores disponibles
   - Selector para elegir preferencia manual
3. Si el farmacéutico elige uno, lo guarda en `Preferencia`

---

#### 🎓 Vista: `entrenamiento()`
```python
def entrenamiento(request):
    # Modo "entrenamiento" tipo flashcards
```

**¿Qué hace?**
1. Selecciona una oportunidad **aleatoria**
2. Muestra el producto a sustituir
3. Pregunta: "¿Por cuál lo sustituyes?"
4. Muestra la respuesta correcta
5. Botón "Siguiente" para otra pregunta

**Analogía:** Como tarjetas de estudio (flashcards) para memorizar sustituciones.

---

#### 🎯 Vista: `examen()`
```python
def examen(request):
    # Modo quiz interactivo
```

**¿Qué hace?**
1. Genera una pregunta con **múltiples opciones**
2. El usuario elige una respuesta
3. Valida si es correcta
4. Muestra feedback
5. Lleva un **contador de aciertos**

---

### 3️⃣ `core/services.py` - Conexión con Databricks

```python
def sincronizar_desde_databricks(farmacia_id='HF280050001'):
    """
    Conecta a Databricks, ejecuta una query SQL y carga datos en Django
    """
```

**¿Qué hace?**
1. Se conecta a **Databricks** (base de datos en la nube)
2. Ejecuta una **consulta SQL** que calcula oportunidades
3. Descarga los resultados
4. Los guarda en la tabla `Oportunidad` de Django

**¿Cuándo se ejecuta?**
- Manualmente: `python manage.py sync_db`
- Desde el panel de admin
- Desde una vista web con botón "Sincronizar"

---

### 4️⃣ `core/urls.py` - Rutas de Core

```python
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('oportunidades/', views.oportunidades, name='oportunidades'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('entrenamiento/', views.entrenamiento, name='entrenamiento'),
    path('examen/', views.examen, name='examen'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
```

**Mapa de navegación:**
- `/` → Dashboard principal
- `/oportunidades/` → Tabla completa
- `/configuracion/` → Preferencias
- `/entrenamiento/` → Modo flashcards
- `/examen/` → Modo quiz
- `/login/` → Pantalla de login
- `/logout/` → Cerrar sesión

---

### 5️⃣ `core/forms.py` - Formularios

```python
class PreferenciaForm(forms.Form):
    laboratorio_preferente = forms.ChoiceField(choices=[])
    activo = forms.BooleanField(required=False, initial=True)
```

**¿Qué hace?**
- Define un **formulario HTML** para elegir laboratorios
- Valida que los datos sean correctos
- Se usa en la vista `configuracion()`

---

### 6️⃣ `core/context_processors.py` - Datos Globales

```python
def contexto_global(request):
    return {
        'tip_del_dia': mensaje_aleatorio,
        'farmacias_disponibles': lista_farmacias,
        'farmacia_activa': farmacia_actual
    }
```

**¿Qué hace?**
- Hace que ciertas variables estén **disponibles en TODAS las plantillas**
- Ejemplo: El "Tip del día" aparece en todas las páginas sin tener que pasarlo manualmente

---

### 7️⃣ `core/templates/` - Plantillas HTML

#### Base: `base.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}{% endblock %}</title>
</head>
<body>
    <nav><!-- Menú de navegación --></nav>
    
    {% block content %}
    <!-- Aquí va el contenido específico de cada página -->
    {% endblock %}
</body>
</html>
```

**¿Qué hace?**
- Define la **estructura común** de todas las páginas
- Otras plantillas **heredan** de esta

#### Dashboard: `dashboard.html`
```html
{% extends 'core/base.html' %}

{% block content %}
    <h1>Dashboard</h1>
    <div>Top 5 Oportunidades:</div>
    {% for item in top_5 %}
        <div>{{ item.grupo_homogeneo }}</div>
    {% endfor %}
{% endblock %}
```

**¿Qué hace?**
- Hereda de `base.html`
- Muestra las top 5 oportunidades
- Usa datos de la vista `dashboard()`

---

### 8️⃣ `core/templatetags/farma_filters.py` - Filtros Personalizados

```python
@register.filter
def euros(value):
    """Formatea números como euros: 1234.56 → 1,234.56"""
    return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
```

**¿Qué hace?**
- Crea **filtros personalizados** para templates
- Uso: `{{ total_ahorro|euros }}`
- Resultado: `1234.56` → `1.234,56`

---

## 💊 NIVEL 4: APP EFP (`efp/`)

La app `efp` es **casi idéntica** a `core`, pero para productos de **Especialidades Farmacéuticas** (otro segmento de negocio).

**Estructura:**
- `efp/models.py` → Modelo `OportunidadEFP` (similar a `Oportunidad`)
- `efp/views.py` → Vistas de dashboard, oportunidades, etc.
- `efp/services.py` → Sincronización con Databricks
- `efp/urls.py` → Rutas con prefijo `/efp/`
- `efp/templates/` → Plantillas HTML específicas

**Diferencias clave:**
- Usa una **tabla distinta** en Databricks
- Los campos del modelo son ligeramente diferentes
- El prefijo de las URLs es `/efp/`

---

## 🔍 ANÁLISIS DE REDUNDANCIAS

Ahora que entendemos todo, veamos las **redundancias detectadas**:

### ❌ REDUNDANCIA 1: Código duplicado entre `core` y `efp`

**Problema:**
- `core/views.py` y `efp/views.py` tienen código casi idéntico
- `core/services.py` y `efp/services.py` son muy similares
- Los templates tienen la misma estructura

**Solución potencial:**
- Crear una **clase base** para las vistas
- Usar **herencia** para evitar duplicación
- Unificar templates con variables condicionales

---

### ❌ REDUNDANCIA 2: Lógica repetida en `get_competidores_stats()`

**Problema:**
- `core/models.py` y `efp/models.py` tienen métodos casi idénticos

**Solución potencial:**
- Crear una **clase abstracta** base
- Mover el método a un módulo compartido `utils.py`

---

### ❌ REDUNDANCIA 3: Queries SQL similares

**Problema:**
- `services.py` de ambas apps ejecutan queries muy parecidas

**Solución potencial:**
- Crear una función genérica `sincronizar(tabla, modelo, farmacia_id)`

---

### ❌ REDUNDANCIA 4: Templates duplicados

**Problema:**
- `core/templates/` y `efp/templates/` tienen archivos casi iguales

**Solución potencial:**
- Crear un directorio `shared_templates/`
- Usar variables de contexto para diferenciar

---

## 📋 RESUMEN EJECUTIVO

### ✅ Lo que está BIEN:
1. **Separación clara** entre config, core y efp
2. **Modelos bien definidos** con campos descriptivos
3. **Vistas organizadas** por funcionalidad
4. **Decoradores de seguridad** (`@login_required`)
5. **Context processors** para datos globales
6. **Filtros personalizados** para formateo

### ⚠️ Lo que podría MEJORAR:
1. **Reducir duplicación** entre core y efp
2. **Extraer lógica común** a módulos compartidos
3. **Crear clases base** para vistas similares
4. **Unificar templates** con herencia
5. **Agregar tests** (actualmente no hay)
6. **Documentar mejor** funciones complejas
7. **Manejar errores** de conexión a Databricks

---

## 🎯 PRÓXIMOS PASOS SUGERIDOS

1. **Entender bien el flujo actual** ✅ (Este documento)
2. **Identificar redundancias** ✅ (Listado arriba)
3. **Crear plan de refactorización** 📝
4. **Implementar mejoras** (paso a paso)
5. **Agregar tests unitarios**
6. **Optimizar queries SQL**

---

¿Quieres que profundice en algún archivo específico o empezamos a planificar la refactorización?

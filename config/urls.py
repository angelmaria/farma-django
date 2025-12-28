from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Delegamos todo lo que empieza por 'efp/' a la app de EFP
    path('efp/', include('efp.urls')),
    
    # Delegamos el resto (la raíz y todo lo demás) a la app CORE
    # Es importante que esta vaya al final si usas rutas vacías ''
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
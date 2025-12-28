import csv
import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Descarga imágenes de EFP desde el archivo CSV local en efp/data/'

    def handle(self, *args, **kwargs):
        # 1. Definir Rutas
        # Ahora buscamos en la carpeta ordenada 'efp/data'
        csv_path = os.path.join(settings.BASE_DIR, 'efp', 'data', 'efp_fotos.csv')
        img_folder = os.path.join(settings.MEDIA_ROOT, 'efp_imagenes')

        # Crear carpeta de destino si no existe
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
            self.stdout.write(self.style.SUCCESS(f'Carpeta de imágenes creada: {img_folder}'))

        # 2. Verificar CSV
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No encuentro el archivo en: {csv_path}'))
            return

        self.stdout.write(f"Leyendo CSV desde: {csv_path}")

        # 3. Procesar
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Tu CSV parece estándar (separado por comas), DictReader lo detectará bien
            reader = csv.DictReader(f)
            
            count = 0
            errors = 0
            skipped = 0
            
            for row in reader:
                # Usamos .get() para evitar fallos si la columna se llama ligeramente distinto
                cn = row.get('Codigo Nacional', '').strip()
                url = row.get('Imagen_URL', '').strip()

                if cn and url and url.startswith('http'):
                    filename = f"{cn}.jpg"
                    filepath = os.path.join(img_folder, filename)

                    # Si ya existe, nos la saltamos para ganar tiempo
                    if os.path.exists(filepath):
                        skipped += 1
                        continue

                    try:
                        # User-Agent para que no nos bloqueen por parecer un bot
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        response = requests.get(url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            with open(filepath, 'wb') as img_file:
                                img_file.write(response.content)
                            count += 1
                            if count % 20 == 0:
                                self.stdout.write(f"Descargadas: {count}...")
                        else:
                            self.stdout.write(self.style.WARNING(f'Error {response.status_code} URL para CN {cn}'))
                            errors += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Excepción en CN {cn}: {e}'))
                        errors += 1
                else:
                    # Fila sin foto o sin CN válido
                    pass

        self.stdout.write(self.style.SUCCESS('--------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS(f'FIN. Descargadas: {count} | Saltadas (ya existían): {skipped} | Errores: {errors}'))
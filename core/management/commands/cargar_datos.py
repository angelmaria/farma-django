from django.core.management.base import BaseCommand
from core.models import Oportunidad

class Command(BaseCommand):
    help = 'Carga datos iniciales de FarmaSwitch'

    def handle(self, *args, **kwargs):
        # Datos extraídos de tu ejemplo (pongo 5 para no hacer el código eterno,
        # puedes añadir el resto aquí siguiendo el patrón)
        datos = [
            ["SITAGLIPTINA HIDROCLORURO ,METFORMINA HIDROCLORURO", "SITAGLIPTINA/METFORMINA STADA 50 MG/1000 MG", 28.30, 6.34, 77.61, 1.4, "EFFICIB 50 mg/1...(58) || JANUMET 50 mg/1...(44)", 2891.30],
            ["LETROZOL", "LETROZOL STADA 2,5 mg", 92.10, 35.40, 61.56, 30.6, "LOXIFAN 2,5MG 3...(24) || FEMARA 2.5MG 30...(21)", 1847.29],
            ["TRAMADOL HIDROCLORURO,PARACETAMOL", "TRAMADOL/PARACETAMOL STADA 37,5 mg", 8.88, 3.20, 63.93, 29.2, "ZALDIAR 37,5 mg...(286) || PAZITAL 37,5 mg...(53)", 1196.60],
            ["MONTELUKAST SODICO", "MONTELUKAST TEVA 10 mg", 21.06, 4.23, 79.91, 2.6, "SINGULAIR 10MG ...(58)", 1173.24],
            ["METAMIZOL MAGNESICO", "METAMIZOL STADA 575MG 20 CAPSULAS", 2.26, 0.83, 63.09, 31.6, "NOLOTIL 575MG 2...(1311)", 1055.60],
        ]

        Oportunidad.objects.all().delete() # Limpiar antes de cargar
        
        for d in datos:
            Oportunidad.objects.create(
                grupo_homogeneo=d[0], producto_recomendado=d[1], pvp_medio=d[2],
                puc_medio=d[3], margen_pct=d[4], penetracion_pct=d[5],
                a_sustituir=d[6], ahorro_potencial=d[7]
            )
        self.stdout.write(self.style.SUCCESS('Datos cargados correctamente'))
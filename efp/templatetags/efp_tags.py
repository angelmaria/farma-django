from django import template

register = template.Library()

@register.filter
def efp_icon(id_agrupacion):
    """
    Mapeo completo de las 76 categorías EFP a iconos FontAwesome.
    """
    iconos = {
        # --- RESPIRATORIO ---
        1: 'fa-lungs-virus',         # TOS PRODUCTIVA
        2: 'fa-head-side-cough',     # TOS SECA
        3: 'fa-thermometer-three-quarters', # ANTIGRIPALES CON DESCONGESTIVO
        77: 'fa-thermometer-half',   # ANTIGRIPALES SIN ANTITUSIVO
        78: 'fa-thermometer-full',   # ANTIGRIPALES SIN DESCONGESTIVO
        79: 'fa-temperature-low',    # ANTIGRIPALES BASICOS
        5: 'fa-virus',               # GRIPE Y RESFRIADO
        6: 'fa-spray-can',           # DESCONGESTIVOS NASALES
        7: 'fa-allergies',           # ANTIHISTAMINICOS
        75: 'fa-user-shield',        # ANTIHISTAMINICOS CON DESCONGESTIVO
        41: 'fa-microphone-alt',     # BUCOFARINGEOS
        
        # --- OJOS Y OIDOS ---
        8: 'fa-eye',                 # ALERGIA OCULAR
        40: 'fa-eye-dropper',        # COLIRIOS HUMECTANTES
        52: 'fa-deaf',               # HIGIENE OIDO

        # --- DIGESTIVO ---
        9: 'fa-fire-alt',            # ANTIACIDOS
        10: 'fa-prescription-bottle',# IBP (Protectores)
        11: 'fa-poop',               # LAXANTES CONTACTO
        12: 'fa-tint',               # LAXANTES OSMOTICOS
        13: 'fa-oil-can',            # LAXANTES SUAVIZANTES
        14: 'fa-syringe',            # ENEMAS
        80: 'fa-capsules',           # LAXANTES SUPOSITORIOS
        86: 'fa-baby',               # ENEMAS INFANTILES
        87: 'fa-baby-carriage',      # SUPOSITORIOS INFANTILES
        88: 'fa-glass-whiskey',      # LAXANTES VOLUMEN
        15: 'fa-stop-circle',        # ANTIDIARREICOS
        16: 'fa-bacterium',          # PROBIOTICOS ANTIDIARREICOS
        67: 'fa-shield-virus',       # ADSORBENTES
        17: 'fa-wind',               # GASES
        18: 'fa-utensils',           # DIGESTION
        43: 'fa-weight',             # SOBREPESO
        44: 'fa-leaf',               # DRENANTES
        54: 'fa-pizza-slice',        # APETITO ESTIMULANTES
        71: 'fa-wine-bottle',        # HEPATOPROTECTOR

        # --- DOLOR ---
        20: 'fa-pills',              # ANALGESICOS ADULTOS
        21: 'fa-child',              # ANALGESICOS PEDIATRICOS
        22: 'fa-tablets',            # PARACETAMOL ADULTOS
        23: 'fa-baby',               # PARACETAMOL PEDIATRICOS
        85: 'fa-capsules',           # PARACETAMOL E IBUPROFENO
        89: 'fa-plus-circle',        # ANALGESICOS COMBINADOS
        24: 'fa-running',            # DOLOR MUSCULAR TOPICO
        81: 'fa-walking',            # DOLOR MUSCULAR ORAL

        # --- SISTEMA NERVIOSO ---
        25: 'fa-bed',                # INSOMNIO FITOTERAPIA
        26: 'fa-moon',               # INSOMNIO ANTIHISTAMINICOS
        27: 'fa-bolt',               # ENERGIA Y VITALIDAD
        28: 'fa-car',                # MAREO
        45: 'fa-smoking-ban',        # TABACO 2MG
        46: 'fa-smoking',            # TABACO 4MG
        47: 'fa-sticky-note',        # TABACO PARCHES
        48: 'fa-spray-can',          # TABACO SPRAY

        # --- PIEL Y CABELLO ---
        29: 'fa-pump-soap',          # ANTISEPTICOS
        30: 'fa-sad-tear',           # ACNE
        31: 'fa-kiss',               # HERPES
        32: 'fa-chair',              # HEMORROIDES TOPICAS
        33: 'fa-pills',              # HEMORROIDES ORALES
        34: 'fa-eraser',             # DESPIGMENTANTES
        35: 'fa-hand-holding-water', # PICOR E IRRITACION
        56: 'fa-cube',               # VASELINAS
        57: 'fa-shoe-prints',        # PIE DE ATLETA
        68: 'fa-snowflake',          # CASPA
        69: 'fa-band-aid',           # CICATRIZANTES
        72: 'fa-foot-prints',        # CALLOS
        73: 'fa-hand-sparkles',      # HONGOS UÑAS
        74: 'fa-hand-point-down',    # VERRUGAS
        36: 'fa-socks',              # VENOTONICOS ORALES
        37: 'fa-leg',                # VENOTONICOS TOPICOS
        49: 'fa-feather-alt',        # ANTICAIDA MINOXIDIL
        82: 'fa-carrot',             # ANTICAIDA NUTRICIONAL

        # --- GINECOLOGIA Y UROLOGIA ---
        38: 'fa-female',             # CANDIDIASIS
        83: 'fa-venus',              # PROBIOTICOS VAGINALES
        39: 'fa-calendar-times',     # ANTICONCEPTIVOS EMERGENCIA
        55: 'fa-fan',                # MENOPAUSIA
        70: 'fa-shower',             # GELES INTIMOS
        51: 'fa-water',              # CISTITIS
        84: 'fa-mars',               # PROSTATA

        # --- OTROS ---
        50: 'fa-apple-alt',          # VITAMINAS
    }
    return iconos.get(id_agrupacion, 'fa-medkit') # Icono por defecto

@register.filter
def efp_family_icon(nombre_familia):
    # Diccionario blindado (Maneja tildes y mayúsculas)
    iconos = {
        "SISTEMA RESPIRATORIO": "fa-lungs",
        "SISTEMA DIGESTIVO": "fa-utensils",
        "SISTEMA NERVIOSO": "fa-brain",
        "DERMATOLOGÍA": "fa-hand-dots",     # Ojo a la tilde
        "DERMATOLOGIA": "fa-hand-dots",     # Por si acaso viene sin tilde
        "SISTEMA CIRCULATORIO": "fa-heart-pulse",
        "SALUD ÍNTIMA": "fa-venus-mars",
        "SALUD INTIMA": "fa-venus-mars",
        "OFTALMOLOGÍA": "fa-eye",
        "OFTALMOLOGIA": "fa-eye",
        "BUCOFARÍNGEOS": "fa-tooth",        # Cambiado a Diente/Boca
        "BUCOFARINGEOS": "fa-tooth",
        "CONTROL DE PESO": "fa-weight-scale",
        "TERAPIA NICOTINA": "fa-ban-smoking",
        "SALUD CAPILAR": "fa-scissors",
        "COMPLEMENTOS": "fa-pills",
        "SISTEMA URINARIO": "fa-droplet",
        "HIGIENE OÍDO": "fa-ear-listen",
        "HIGIENE OIDO": "fa-ear-listen"
    }
    return iconos.get(str(nombre_familia).strip().upper(), "fa-circle-question")

@register.filter
def efp_family_color(nombre_familia):
    """Devuelve una tupla (Fondo, Texto/Borde) según la familia"""
    # Formato: "Nombre": ("FondoHex", "TextoHex")
    colores = {
        "SISTEMA RESPIRATORIO": ("#e0f7fa", "#006064"), # Cyan
        "SISTEMA DIGESTIVO":    ("#fff3e0", "#e65100"), # Naranja
        "SISTEMA NERVIOSO":     ("#f3e5f5", "#7b1fa2"), # Púrpura
        "DOLOR":                ("#ffebee", "#c62828"), # Rojo
        "DERMATOLOGÍA":         ("#fce4ec", "#880e4f"), # Rosa
        "DERMATOLOGIA":         ("#fce4ec", "#880e4f"),
        "SISTEMA CIRCULATORIO": ("#e8eaf6", "#1a237e"), # Indigo
        "SALUD ÍNTIMA":         ("#f8bbd0", "#c2185b"), # Rosa fuerte
        "SALUD INTIMA":         ("#f8bbd0", "#c2185b"),
        "OFTALMOLOGÍA":         ("#e1f5fe", "#01579b"), # Azul claro
        "OFTALMOLOGIA":         ("#e1f5fe", "#01579b"),
        "BUCOFARÍNGEOS":        ("#e0f2f1", "#004d40"), # Teal
        "BUCOFARINGEOS":        ("#e0f2f1", "#004d40"),
        "CONTROL DE PESO":      ("#f1f8e9", "#33691e"), # Verde lima
        "TERAPIA NICOTINA":     ("#eceff1", "#37474f"), # Gris azulado
        "SALUD CAPILAR":        ("#fff8e1", "#ff6f00"), # Ambar
        "COMPLEMENTOS":         ("#fffde7", "#f57f17"), # Amarillo
        "SISTEMA URINARIO":     ("#e3f2fd", "#0d47a1"), # Azul
        "HIGIENE OÍDO":         ("#efebe9", "#4e342e"), # Marrón
        "HIGIENE OIDO":         ("#efebe9", "#4e342e")
    }
    return colores.get(str(nombre_familia).strip().upper(), ("#ffffff", "#6c757d"))
from django import template

register = template.Library()

@register.filter
def euros(value):
    """
    Convierte un número a formato español sin decimales de forma manual.
    Ej: 33190.50 -> "33.191"
    """
    try:
        # 1. Convertimos a float
        val = float(value)
        # 2. Formateamos usando la coma como separador de miles (formato estándar python)
        #    Esto nos dará "33,190"
        s = '{:,.0f}'.format(val)
        # 3. Cambiamos la coma por punto
        return s.replace(',', '.')
    except (ValueError, TypeError):
        return value
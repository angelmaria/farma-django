from django import forms
from .models import Preferencia

class PreferenciaForm(forms.ModelForm):
    class Meta:
        model = Preferencia
        fields = ['laboratorio_preferente', 'activo']
        widgets = {
            'laboratorio_preferente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: STADA, CINFA...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
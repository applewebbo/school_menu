from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Div, Field, Layout, Submit
from django import forms
from django.urls import reverse

from school_menu.models import School


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "city", "season_choice", "week_bias", "menu_type"]
        widgets = {
            "season_choice": forms.Select(attrs={"class": "form-select"}),
            "week_bias": forms.NumberInput(),
            "menu_type": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "name": "Nome",
            "city": "Città",
            "season_choice": "Stagione",
            "week_bias": "Scarto",
            "menu_type": "Tipo di Menù",
        }
        help_texts = {
            "season_choice": "Selezionando Automatico il sistema sceglierà la stagione in base alla data attuale",
            "week_bias": "Modificare il valore per allineare la settimana in corso (max=3)",
            "menu_type": "Seleziona Semplice per un singolo campo, Dettagliato per avere menu diviso in primo, secondo, contorno e spuntino",
        }
        error_messages = {
            "week_bias": {
                "max_value": "Il valore massimo è 3",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    "name",
                    "city",
                    "menu_type",
                ),
                Div(
                    "season_choice",
                    "week_bias",
                ),
                css_class="grid grid-cols-1 md:grid-cols-2 md:gap-4",
            ),
            Div(
                Submit(
                    "submit",
                    "Salva",
                    css_class="w-full md:w-auto btn btn-sm btn-primary mt-2",
                ),
                css_class="md:text-right",
            ),
        )


class UploadMenuForm(forms.Form):
    file = forms.FileField(label="Carica File")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Field(
                    "file",
                    css_class="file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-300 text-slate-500 text-sm",
                ),
                Submit(
                    "submit",
                    "Salva",
                    css_class="btn btn-sm btn-primary ms-2",
                ),
                Button(
                    "cancel",
                    "Annulla",
                    css_class="btn btn-sm btn-danger-outline ms-2",
                    hx_get=reverse("school_menu:cancel_upload_menu"),
                ),
                css_class="flex items-start justify-center",
            ),
        )

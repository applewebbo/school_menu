from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Submit
from django import forms

from school_menu.models import DetailedMeal, Meal, School, SimpleMeal


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
            "season_choice": "Selezionando AUTOMATICA il sistema sceglierà la stagione in base alla data attuale",
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
    season = forms.ChoiceField(
        choices=Meal.Seasons.choices,
        label="Stagionalità",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    file = forms.FileField(label="Carica Menu")

    def clean_file(self):
        file = self.cleaned_data.get("file")
        ext = file.name.split(".")[-1].lower()
        if ext not in ["xls", "xlsx"]:
            raise forms.ValidationError("Il file deve essere in formato xls o xlsx")
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "season",
            Field(
                "file",
                css_class="file-upload-input mb-2",
                accept=".xls, .xlsx",
            ),
        )


class SimpleMealForm(forms.ModelForm):
    class Meta:
        model = SimpleMeal
        fields = ["menu", "snack"]
        labels = {
            "menu": "Menù",
            "snack": "Spuntino",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("menu", css_class="h-36"),
            "snack",
        )


class DetailedMealForm(forms.ModelForm):
    class Meta:
        model = DetailedMeal
        fields = ["first_course", "second_course", "side_dish", "fruit", "snack"]
        labels = {
            "first_course": "Primo",
            "second_course": "Secondo",
            "side_dish": "Contorno",
            "fruit": "Frutta",
            "snack": "Spuntino",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "first_course",
            "second_course",
            "side_dish",
            "fruit",
            "snack",
        )

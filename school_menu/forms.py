from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Fieldset, Layout, Submit
from django import forms

from school_menu.models import DetailedMeal, Meal, School, SimpleMeal


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            "name",
            "city",
            "season_choice",
            "week_bias",
            "menu_type",
            "is_published",
            "no_gluten",
            "no_lactose",
            "vegetarian",
            "special",
            "annual_menu",
        ]
        widgets = {
            "season_choice": forms.Select(attrs={"class": "form-select"}),
            "week_bias": forms.NumberInput(),
            "menu_type": forms.Select(attrs={"class": "form-select"}),
            "is_published": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-secondary"}
            ),
            "no_gluten": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-secondary"}
            ),
            "no_lactose": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-secondary"}
            ),
            "vegetarian": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-secondary"}
            ),
            "special": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-secondary"}
            ),
            "annual_menu": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-secondary"}
            ),
        }
        labels = {
            "name": "Nome",
            "city": "Città",
            "season_choice": "Stagione",
            "week_bias": "Scarto",
            "menu_type": "Tipo di Menù",
            "is_published": "Pubblico",
            "no_gluten": "No Glutine",
            "no_lactose": "No Lattosio",
            "vegetarian": "Vegetariano",
            "special": "Speciale",
            "annual_menu": "Menu Annuale",
        }
        help_texts = {
            "season_choice": "Selezionando AUTOMATICA il sistema sceglierà la stagione in base alla data corrente, altrimenti rimarrà fissa al valore selezionato",
            "week_bias": "Modificare il valore per allineare la settimana in corso (max=3)",
            "menu_type": "Seleziona Semplice per menu unificato + spuntino, Dettagliato per avere menu diviso in primo, secondo, contorno e frutta + spuntino",
            "is_published": "Seleziona per rendere il menù visibile agli utenti",
            "no_gluten": "No Glutine",
            "no_lactose": "No Lattosio",
            "vegetarian": "Vegetariano",
            "special": "Speciale",
            "annual_menu": "Seleziona se la tua scuola fornisce un menu completo relativo a tutto l'anno. Selezionando questo campo non verranno considerati i valori dei campi Stagione e Scarto.",
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
        self.fields["no_gluten"].label = False
        self.fields["no_lactose"].label = False
        self.fields["vegetarian"].label = False
        self.fields["special"].label = False
        self.helper.layout = Layout(
            Div(
                Div("name", "city", "menu_type", "is_published"),
                Div(
                    "season_choice",
                    "annual_menu",
                    "week_bias",
                ),
                Fieldset(
                    "Menu Alternativi",
                    Div("no_gluten", css_class="flex items-center me-4"),
                    Div("no_lactose", css_class="flex items-center me-4"),
                    Div("vegetarian", css_class="flex items-center me-4"),
                    Div("special", css_class="flex items-center me-4"),
                    css_class="flex col-span-1 md:col-span-2",
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
        if ext not in ["csv"]:
            raise forms.ValidationError("Il file deve essere in formato csv")
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "season",
            Div(
                Field(
                    "file",
                    css_class="file-input file-input-sm file-input-bordered mb-2",
                    accept=".csv",
                ),
                Div(
                    css_id="spinner",
                    css_class="loading loading-bars loading-md ms-6 mt-2 text-primary htmx-indicator",
                ),
                css_class="flex flex-row gap-2",
            ),
        )


class UploadAnnualMenuForm(forms.Form):
    file = forms.FileField(label="Carica Menu")

    def clean_file(self):
        file = self.cleaned_data.get("file")
        ext = file.name.split(".")[-1].lower()
        if ext not in ["csv"]:
            raise forms.ValidationError("Il file deve essere in formato csv")
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field(
                    "file",
                    css_class="file-input file-input-sm file-input-bordered mb-2",
                    accept=".csv",
                ),
                Div(
                    css_id="spinner",
                    css_class="loading loading-bars loading-md ms-6 mt-2 text-primary htmx-indicator",
                ),
                css_class="flex flex-row gap-2",
            )
        )


class SimpleMealForm(forms.ModelForm):
    class Meta:
        model = SimpleMeal
        fields = ["menu", "morning_snack", "afternoon_snack"]
        labels = {
            "menu": "Menù",
            "morning_snack": "Spuntino mattino",
            "afternoon_snack": "Merenda pomeriggio",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("menu", css_class="h-36"),
            "morning_snack",
            "afternoon_snack",
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

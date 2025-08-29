from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Div, Field, Fieldset, Layout, Submit
from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe

from school_menu.models import DetailedMeal, Meal, School, SimpleMeal


class SchoolForm(forms.ModelForm):
    start_date = forms.DateField(
        label="Inizio",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end_date = forms.DateField(
        label="Fine",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

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
            "name": forms.TextInput(),
            "city": forms.TextInput(),
            "season_choice": forms.Select(attrs={"class": "select"}),
            "week_bias": forms.NumberInput(attrs={"min": "0", "max": "3"}),
            "menu_type": forms.Select(attrs={"class": "select"}),
            "is_published": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-primary"}
            ),
            "no_gluten": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-primary"}
            ),
            "no_lactose": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-primary"}
            ),
            "vegetarian": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-primary"}
            ),
            "special": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-primary"}
            ),
            "annual_menu": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm checkbox-primary"}
            ),
        }
        labels = {
            "name": "Nome",
            "city": "Città",
            "season_choice": "Stagione",
            "week_bias": "Scarto",
            "menu_type": mark_safe(  # nosec B308
                'Tipo&nbsp;<span class="hidden sm:block">di Menù</span>'
            ),
            "is_published": "Menu Pubblico",
            "no_gluten": "No Glutine",
            "no_lactose": "No Lattosio",
            "vegetarian": "Vegetariano",
            "special": "Speciale",
            "annual_menu": "Menu Annuale",
        }
        help_texts = {
            "season_choice": "Selezionando <strong>Automatica</strong> il sistema sceglierà la stagione in base alla data corrente",
            "week_bias": "Modificare il valore per allineare la settimana in corso (min=0, max=3)",
            "menu_type": "Seleziona <strong>Semplice</strong> per menu + spuntino, <strong>Dettagliato</strong> per avere primo, secondo, contorno e frutta + spuntino",
            "is_published": "Seleziona per rendere il menù visibile agli altri utenti",
            "annual_menu": "Seleziona se la tua scuola fornisce un menu specifico per ogni giorno dell'anno. Selezionando questo campo non verranno considerati i valori dei campi Stagione, Scarto e Anno Scolastico.",
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
                    HTML("""<hr class="hr_divider" />"""),
                    "menu_type",
                    Div("is_published", css_class="ms-1"),
                    HTML("""<hr class="hr_divider" />"""),
                    Fieldset(
                        "Anno Scolastico",
                        "start_date",
                        "end_date",
                        HTML("""
                            <p class="text-base-content/70 text-sm leading-5">
                            Seleziona data di inizio e fine anno scolastico. Solo all'interno di questo periodo sono attive le notifiche del menu.</p>
                            <hr class="hr_divider md:hidden" />
                        """),
                        css_class="fieldset",
                    ),
                ),
                Div(
                    "season_choice",
                    "annual_menu",
                    HTML("""<hr class="hr_divider" />"""),
                    "week_bias",
                    HTML("""<hr class="hr_divider md:hidden" />"""),
                ),
                Fieldset(
                    "Menu Alternativi",
                    Div("no_gluten", css_class="flex items-center me-4"),
                    Div("no_lactose", css_class="flex items-center me-4"),
                    Div("vegetarian", css_class="flex items-center me-4"),
                    Div("special", css_class="flex items-center me-4"),
                    css_class="flex flex-wrap col-span-1 md:col-span-2 fieldset",
                ),
                css_class="grid grid-cols-1 md:grid-cols-2 md:gap-6",
            ),
            Div(
                Div(
                    css_id="spinner",
                    css_class="loading loading-bars loading-md text-primary mt-0 md:mt-2 md:me-4 self-center htmx-indicator",
                ),
                Button(
                    "cancel",
                    "Annulla",
                    css_class="w-full md:w-auto btn btn-sm btn-error mt-2",
                    **{
                        "hx-get": reverse("school_menu:school_settings"),
                        "hx-target": "#school",
                        "hx-swap": "outerHTML",
                    },
                ),
                Submit(
                    "submit",
                    "Salva",
                    css_class="w-full md:w-auto btn btn-sm btn-primary mt-2",
                ),
                css_class="flex flex-col md:flex-row md:justify-end md:mx-auto items-center gap-2",
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
        widgets = {
            "menu": forms.Textarea(),
            "morning_snack": forms.TextInput(),
            "afternoon_snack": forms.TextInput(),
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
        widgets = {
            "first_course": forms.TextInput(),
            "second_course": forms.TextInput(),
            "side_dish": forms.TextInput(),
            "fruit": forms.TextInput(),
            "snack": forms.TextInput(),
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

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Div, Field, Fieldset, Layout, Submit
from django import forms
from django.conf import settings
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.safestring import mark_safe

from school_menu.ai.normalise import (
    ANNUAL_MENU_MAX_LENGTH,
    COURSE_MAX_LENGTH,
    DATE_FORMAT,
    MAX_WEEK,
    MENU_MAX_LENGTH,
    MIN_WEEK,
    SNACK_MAX_LENGTH,
    WEEKDAYS,
)
from school_menu.models import (
    DetailedMeal,
    Meal,
    MenuImportDraft,
    School,
    SimpleMeal,
)

# Only CSV goes through the classic validation; the others exist so a file the user
# already has can be handed to the AI instead of being retyped by hand.
CSV_EXTENSION = "csv"
AI_EXTENSIONS = ["pdf", "xlsx"]


def allowed_upload_extensions():
    """CSV always; the AI formats only while the import is actually available."""
    if settings.AI_MENU_IMPORT_ENABLED:
        return [CSV_EXTENSION, *AI_EXTENSIONS]
    return [CSV_EXTENSION]


def validate_menu_upload(file):
    """Refuse anything we could not read, before it costs a request or a quota slot."""
    _, _, extension = file.name.rpartition(".")
    allowed = allowed_upload_extensions()
    if extension.lower() not in allowed:
        formats = ", ".join(allowed)
        raise forms.ValidationError(f"Il file deve essere in formato {formats}")
    max_size = settings.AI_MENU_IMPORT_MAX_FILE_SIZE
    if file.size > max_size:
        raise forms.ValidationError(
            f"Il file non può superare i {max_size // (1024 * 1024)} MB"
        )
    return file


class DaisyErrorClassMixin:
    """
    Mark the offending control itself, not just the message under it.

    daisyUI signals an invalid field with an `*-error` class, which has to sit on the
    widget. The widget cannot know until the form has been cleaned, so the class is added
    here rather than in `__init__` — `self.fields` is deep-copied per instance, so this
    never leaks into another form (#239).
    """

    ERROR_CLASSES = {
        forms.Textarea: "textarea-error",
        forms.Select: "select-error",
    }

    def full_clean(self):
        super().full_clean()
        for name, field in self.fields.items():
            if name not in self.errors:
                continue
            widget = field.widget
            error_class = self.ERROR_CLASSES.get(type(widget), "input-error")
            widget.attrs["class"] = (
                f"{widget.attrs.get('class', '')} {error_class}".strip()
            )


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

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        city = cleaned_data.get("city")

        if name and city:
            # Generate the slug that would be created
            potential_slug = slugify(f"{name}-{city}")

            # Check if a school with this slug already exists
            # Exclude current instance on updates
            existing_schools = School.objects.filter(slug=potential_slug)
            if self.instance.pk:
                existing_schools = existing_schools.exclude(pk=self.instance.pk)

            if existing_schools.exists():
                raise forms.ValidationError(
                    f"Esiste già una scuola con nome '{name}' nella città '{city}'. "
                    f"Scegli un nome diverso o aggiungi ulteriori dettagli "
                    f"(es. '{name} Via Rossi')."
                )

        return cleaned_data

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
        return validate_menu_upload(self.cleaned_data.get("file"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "season",
            # The submit indicator is not part of the layout: htmx-indicator only toggles
            # opacity, so a spinner sitting beside the field keeps its width reserved and
            # leaves the field visibly narrower than the ones above it. It lives next to the
            # Salva button in upload-menu.html instead (#241).
            Field(
                "file",
                css_class="file-input file-input-sm file-input-bordered w-full",
                accept=",".join(f".{ext}" for ext in allowed_upload_extensions()),
            ),
        )


class UploadAnnualMenuForm(forms.Form):
    file = forms.FileField(label="Carica Menu")

    def clean_file(self):
        return validate_menu_upload(self.cleaned_data.get("file"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field(
                    "file",
                    # w-full + a growing wrapper, or the flex row shrinks the field to its
                    # content and it no longer lines up with the fields above it (#241).
                    css_class="file-input file-input-sm file-input-bordered w-full",
                    wrapper_class="grow",
                    accept=",".join(f".{ext}" for ext in allowed_upload_extensions()),
                ),
                Div(
                    css_id="spinner",
                    css_class="loading loading-bars loading-md text-primary htmx-indicator shrink-0",
                ),
                css_class="flex w-full flex-row items-center gap-2",
            )
        )


class SimpleMealForm(DaisyErrorClassMixin, forms.ModelForm):
    class Meta:
        model = SimpleMeal
        fields = ["menu", "morning_snack", "afternoon_snack"]
        labels = {
            "menu": "Menù",
            "morning_snack": "Spuntino mattino",
            "afternoon_snack": "Merenda pomeriggio",
        }
        widgets = {
            # Rendered field by field in create-weekly-menu.html rather than by crispy, so
            # the page matches the AI preview: the classes have to live here (#239).
            "menu": forms.Textarea(
                attrs={"class": "textarea textarea-sm w-full", "rows": 3}
            ),
            "morning_snack": forms.TextInput(attrs={"class": "input input-sm w-full"}),
            "afternoon_snack": forms.TextInput(
                attrs={"class": "input input-sm w-full"}
            ),
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


class DetailedMealForm(DaisyErrorClassMixin, forms.ModelForm):
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
            "first_course": forms.TextInput(attrs={"class": "input input-sm w-full"}),
            "second_course": forms.TextInput(attrs={"class": "input input-sm w-full"}),
            "side_dish": forms.TextInput(attrs={"class": "input input-sm w-full"}),
            "fruit": forms.TextInput(attrs={"class": "input input-sm w-full"}),
            "snack": forms.TextInput(attrs={"class": "input input-sm w-full"}),
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


# ---------------------------------------------------------------------------
# AI menu import (#234)
# ---------------------------------------------------------------------------

# Rows are edited with plain forms, not the ModelForms above: those are bound to saved
# instances and deliberately exclude `day` and `week`, which are exactly the two fields
# the AI gets wrong most often and the user must be able to correct. Building model rows
# just to preview them would also publish a menu that has not been confirmed yet.


def _row_field(max_length, widget=None):
    return forms.CharField(
        max_length=max_length,
        required=False,
        strip=True,
        widget=widget or forms.TextInput(attrs={"class": "input input-sm w-full"}),
    )


class AiWeeklyRowForm(DaisyErrorClassMixin, forms.Form):
    giorno = forms.ChoiceField(
        choices=[(day, day) for day in WEEKDAYS],
        widget=forms.Select(attrs={"class": "select select-sm w-full"}),
    )
    settimana = forms.ChoiceField(
        choices=[(week, week) for week in range(MIN_WEEK, MAX_WEEK + 1)],
        widget=forms.Select(attrs={"class": "select select-sm w-full"}),
    )


class AiSimpleRowForm(AiWeeklyRowForm):
    pranzo = _row_field(
        MENU_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={"class": "textarea textarea-sm w-full", "rows": 3}
        ),
    )
    spuntino = _row_field(SNACK_MAX_LENGTH)
    merenda = _row_field(SNACK_MAX_LENGTH)


class AiDetailedRowForm(AiWeeklyRowForm):
    primo = _row_field(COURSE_MAX_LENGTH)
    secondo = _row_field(COURSE_MAX_LENGTH)
    contorno = _row_field(COURSE_MAX_LENGTH)
    frutta = _row_field(COURSE_MAX_LENGTH)
    spuntino = _row_field(COURSE_MAX_LENGTH)


class AiAnnualRowForm(DaisyErrorClassMixin, forms.Form):
    data = forms.DateField(
        input_formats=[DATE_FORMAT],
        widget=forms.TextInput(attrs={"class": "input input-sm w-full"}),
    )
    primo = _row_field(ANNUAL_MENU_MAX_LENGTH)
    secondo = _row_field(ANNUAL_MENU_MAX_LENGTH)
    contorno = _row_field(ANNUAL_MENU_MAX_LENGTH)
    frutta = _row_field(ANNUAL_MENU_MAX_LENGTH)
    altro = _row_field(ANNUAL_MENU_MAX_LENGTH)

    def clean_data(self):
        """Give the date back in the format the CSV resources expect."""
        return self.cleaned_data["data"].strftime(DATE_FORMAT)


AI_ROW_FORMS = {
    MenuImportDraft.Kinds.SIMPLE: AiSimpleRowForm,
    MenuImportDraft.Kinds.DETAILED: AiDetailedRowForm,
    MenuImportDraft.Kinds.ANNUAL: AiAnnualRowForm,
}


class AiKeepRowMixin(forms.Form):
    """
    Rows are kept unless the user says otherwise.

    Deliberately not the formset's own `can_delete`: that renders an unticked "remove"
    box, so the safe state of the control is the one nobody wants, and a stray click
    silently drops a row. A ticked "include" states what will happen to the row, and is
    not mistakeable for a per-row action button the way an imperative would be (#239).
    """

    includi = forms.BooleanField(
        required=False,
        initial=True,
        label="Includi",
        widget=forms.CheckboxInput(
            attrs={"class": "checkbox checkbox-sm checkbox-primary"}
        ),
    )


def ai_row_formset(kind):
    """The formset used to review and correct the rows the AI produced."""
    form = type(
        f"AiKeep{AI_ROW_FORMS[kind].__name__}",
        (AiKeepRowMixin, AI_ROW_FORMS[kind]),
        {},
    )
    return forms.formset_factory(form, extra=0)

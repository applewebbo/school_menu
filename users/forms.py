from allauth.account.forms import SignupForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms


class MyCustomSignupForm(SignupForm):
    tc_agree = forms.BooleanField(
        required=True,
        error_messages={
            "required": "Devi accettare i termini e condizioni per proseguire."
        },
        label="Termini e condizioni",
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-sm me-2"}),
        help_text='Seleziona questo campo per accettare i <a href="/terms-and-conditions/" class="link link-primary">termini e condizioni</a>.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.move_to_end("tc_agree")
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "email",
                "password1",
            ),
            Div(
                "tc_agree",
                css_class="form-control",
            ),
        )

    def save(self, request):
        # Ensure you call the parent class's save.
        # .save() returns a User object.
        user = super().save(request)

        # Add your own processing here.
        user.tc_agree = self.cleaned_data.get("tc_agree")
        user.save()

        # You must return the original result.
        return user

    def clean_tc_agree(self):
        tc_agree = self.cleaned_data.get("tc_agree")
        if not tc_agree:
            raise forms.ValidationError(
                "Devi accettare i termini e condizioni per proseguire."
            )
        return tc_agree

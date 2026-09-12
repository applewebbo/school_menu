from allauth.account.forms import AddEmailForm, LoginForm, SignupForm
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
    # Honeypot (#272): hidden from real users via CSS in signup.html, but naive bots
    # that fill every input on the page populate it, so a non-empty value here means
    # the submission wasn't a human.
    website = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.move_to_end("tc_agree")
        self.fields["email"].widget.attrs.update(
            {"placeholder": "Inserisci la tua email"}
        )
        self.fields["password1"].widget.attrs.update(
            {"placeholder": "Inserisci la tua password"}
        )

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Registrazione non disponibile al momento.")
        return self.cleaned_data.get("website")

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


class MyCustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["login"].label = "Email"
        self.fields["password"].label = "Password"
        self.fields["password"].help_text = None
        self.fields["login"].widget.attrs.update(
            {"placeholder": "Inserisci la tua email"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Inserisci la tua password"}
        )


class MyCustomAddEmailForm(AddEmailForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Indirizzo Email"
        self.fields["email"].widget.attrs.update(
            {
                "class": "input input-bordered w-full",
                "placeholder": "Inserisci il nuovo indirizzo email",
            }
        )

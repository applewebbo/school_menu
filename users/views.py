from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def email_verification_sent(request):
    """
    Replaces allauth's EmailVerificationSentView (#262): the default page had nothing
    to act on besides "go back", so a toast + redirect does the same job without an
    extra page behind the app's navbar.
    """
    messages.add_message(
        request,
        messages.INFO,
        "Ti abbiamo inviato un'email di verifica: segui il link per completare la "
        "registrazione. Se non la trovi, controlla anche nello spam. Attenzione: se "
        f"l'account non viene verificato entro {settings.UNVERIFIED_ACCOUNT_RETENTION_DAYS} "
        "giorni verrà eliminato automaticamente.",
    )
    return redirect("school_menu:index")


def password_reset_done(request):
    """Replaces allauth's PasswordResetDoneView with a toast + redirect (#262)."""
    messages.add_message(
        request,
        messages.INFO,
        "Ti abbiamo inviato un'email con le istruzioni per reimpostare la password. "
        "Se non la trovi, controlla anche nello spam.",
    )
    return redirect("school_menu:index")


def password_reset_from_key_done(request):
    """Replaces allauth's PasswordResetFromKeyDoneView with a toast + redirect (#262)."""
    messages.add_message(
        request,
        messages.SUCCESS,
        "Password cambiata con successo. Accedi con la nuova password.",
    )
    return redirect("account_login")


@login_required
def user_delete(request):
    user = request.user
    if request.method == "POST":
        user.delete()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Utente cancellato con successo",
        )
        return redirect("school_menu:index")
    return render(request, "users/user_delete.html", context={"user": user})

import json

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from pywebpush import WebPushException, webpush

from .forms import AnonymousMenuNotificationForm
from .models import AnonymousMenuNotification


def notification_settings(request):
    pk = request.session.get("anon_notification_pk")
    context = {}
    if pk:
        notification = AnonymousMenuNotification.objects.get(pk=pk)
        context["school"] = notification.school

    context["form"] = AnonymousMenuNotificationForm()
    return render(request, "notifications/notification_settings.html", context)


@require_http_methods(["POST"])
def save_subscription(request):
    form = AnonymousMenuNotificationForm(request.POST)
    if form.is_valid():
        school = form.cleaned_data["school"]
        subscription_info = form.cleaned_data["subscription_info"]
        notification = AnonymousMenuNotification.objects.create(
            school=school, subscription_info=subscription_info
        )
        request.session["anon_notification_pk"] = notification.pk
        request.session.save()
        messages.add_message(
            request, messages.SUCCESS, "Notifiche abilitate con successo"
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        return HttpResponse("error", status=400)


def delete_subscription(request):
    if request.method == "POST":
        try:
            pk = request.session.get("anon_notification_pk")
            if not pk:
                messages.error(request, "Nessuna sottoscrizione trovata.")
                return HttpResponse(status=400, headers={"HX-Refresh": "true"})
            notification = AnonymousMenuNotification.objects.get(pk=pk)
            notification.delete()
            del request.session["anon_notification_pk"]
            messages.add_message(
                request, messages.SUCCESS, "Notifiche disabilitate con successo"
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        except AnonymousMenuNotification.DoesNotExist:
            messages.error(request, "La sottoscrizione non esiste.")
            return HttpResponse(status=404, headers={"HX-Refresh": "true"})
        except Exception as e:
            messages.error(request, f"Errore durante la disabilitazione: {str(e)}")
            return HttpResponse(status=400, headers={"HX-Refresh": "true"})
    messages.error(request, "Richiesta non valida.")
    return HttpResponse(status=405, headers={"HX-Refresh": "true"})


@require_http_methods(["POST"])
def test_notification(request):
    """
    Invia una notifica di prova all'utente iscritto e restituisce una risposta HTML per htmx.
    """
    pk = request.session.get("anon_notification_pk")
    if not pk:
        messages.error(request, "Nessuna sottoscrizione trovata.")
        return render(
            request,
            "notifications/partials/test_notification_result.html",
            {"success": False},
        )

    notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
    payload = {
        "head": "Test Notifica",
        "body": "Questa è una notifica di prova.",
        "icon": "/static/img/notification-bell.png",  # Modifica il path se necessario
        "url": "/",
    }

    try:
        webpush(
            subscription_info=notification.subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
            vapid_claims={
                "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"
            },
        )
        message = (
            "Notifica di prova inviata. Verifica di averla ricevuta sul tuo dispositivo"
        )
        return render(
            request,
            "notifications/partials/test_notification_result.html",
            {"success": True, "message": message},
        )
    except WebPushException as e:
        message = f"Errore durante l'invio: {e}"
        return render(
            request,
            "notifications/partials/test_notification_result.html",
            {"success": False, "message": message},
        )
    except Exception as e:
        message = f"Errore inatteso: {e}"
        return render(
            request,
            "notifications/partials/test_notification_result.html",
            {"success": False, "message": message},
        )

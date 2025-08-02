from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods
from django_q.tasks import async_task
from pywebpush import WebPushException

from notifications.forms import AnonymousMenuNotificationForm
from notifications.models import AnonymousMenuNotification
from notifications.utils import build_menu_notification_payload


def notification_settings(request):
    pk = request.session.get("anon_notification_pk")
    context = {}
    if pk:
        notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
        context["notification"] = notification

    context["form"] = AnonymousMenuNotificationForm()
    return render(request, "notifications/notification_settings.html", context)


def notifications_buttons(request, pk):
    notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
    context = {"notification": notification}
    return render(request, "notifications/notification_settings.html#buttons", context)


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
        return TemplateResponse(
            request,
            "notifications/partials/subscription_form.html",
            {"form": form},
            status=400,
        )


def delete_subscription(request):
    if request.method == "POST":
        pk = request.session.get("anon_notification_pk")
        if not pk:
            messages.error(request, "Nessuna sottoscrizione trovata.")
            return HttpResponse(status=400, headers={"HX-Refresh": "true"})
        try:
            notification = AnonymousMenuNotification.objects.get(pk=pk)
            notification.delete()
            del request.session["anon_notification_pk"]
            messages.add_message(
                request, messages.SUCCESS, "Notifiche disabilitate con successo"
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        except AnonymousMenuNotification.DoesNotExist:
            return HttpResponse(status=404)
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
        message = "Nessuna sottoscrizione trovata."
        messages.error(request, message)
        return render(
            request,
            "notifications/partials/test_notification_result.html",
            {"success": False, "message": message},
        )

    notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
    payload = build_menu_notification_payload(notification.school)
    if not payload:
        payload = {
            "head": "Notifica di prova",
            "body": "Nessun menu previsto per oggi, ma la notifica funziona!",
        }
    payload["icon"] = "/static/img/notification-bell.png"
    payload["url"] = notification.school.get_absolute_url()

    try:
        async_task(
            "notifications.tasks.send_test_notification",
            notification.subscription_info,
            payload,
        )
        message = (
            "Notifica di prova inviata in background. Controlla il tuo dispositivo."
        )
        success = True
    except WebPushException:
        message = "Errore durante l'invio della notifica di prova."
        success = False
    except Exception:
        message = "Errore durante l'invio della notifica di prova."
        success = False

    return render(
        request,
        "notifications/partials/test_notification_result.html",
        {"success": success, "message": message},
    )


@require_http_methods(["POST"])
def toggle_daily_notification(request):
    """
    Attiva o disattiva le notifiche giornaliere per l'utente.
    """
    pk = request.session.get("anon_notification_pk")
    if not pk:
        messages.error(request, "Nessuna sottoscrizione trovata.")
        return HttpResponse(status=400, headers={"HX-Refresh": "true"})

    notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
    notification.daily_notification = not notification.daily_notification
    notification.save()

    if notification.daily_notification:
        message = "Notifiche giornaliere attivate."
    else:
        message = "Notifiche giornaliere disattivate."

    response = TemplateResponse(
        request,
        "notifications/partials/test_notification_result.html",
        {"success": True, "message": message},
    )
    response["HX-Trigger"] = "notificationChanged"
    return response


def change_school(request, pk):
    notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
    if request.method == "POST":
        form = AnonymousMenuNotificationForm(request.POST, instance=notification)
        if form.is_valid():
            form.save()
            message = "Scuola modificata con successo."
            response = TemplateResponse(
                request,
                "notifications/partials/test_notification_result.html",
                {"success": True, "message": message},
            )
            response["HX-Trigger"] = "notificationChanged"
            return response
    else:
        form = AnonymousMenuNotificationForm(instance=notification)

    context = {"form": form, "notification": notification}
    return render(request, "notifications/partials/change_school.html", context)

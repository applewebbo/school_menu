import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from school_menu.models import School

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


@csrf_exempt
def save_subscription(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            school_id = data.get("school_id")
            subscription = data.get("subscription")
            if not school_id or not subscription:
                return JsonResponse(
                    {"success": False, "error": "Missing school or subscription info"},
                    status=400,
                )
            school = School.objects.get(pk=school_id)
            notification = AnonymousMenuNotification.objects.create(
                school=school, subscription_info=subscription
            )
            request.session["anon_notification_pk"] = notification.pk
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=405)


def delete_subscription(request):
    if request.method == "POST":
        try:
            pk = request.session.get("anon_notification_pk")
            if not pk:
                return JsonResponse(
                    {"success": False, "error": "No subscription found"}, status=400
                )
            notification = AnonymousMenuNotification.objects.get(pk=pk)
            notification.delete()
            del request.session["anon_notification_pk"]
            messages.add_message(
                request, messages.SUCCESS, "Notifiche disabilitate con successo"
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        except AnonymousMenuNotification.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Subscription does not exist"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=405)

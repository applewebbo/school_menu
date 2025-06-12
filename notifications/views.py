import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from school_menu.models import School

from .forms import AnonymousMenuNotificationForm
from .models import AnonymousMenuNotification


def notification_settings(request):
    form = AnonymousMenuNotificationForm()
    return render(request, "notifications/notification_settings.html", {"form": form})


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
            AnonymousMenuNotification.objects.create(
                school=school, subscription_info=subscription
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=405)

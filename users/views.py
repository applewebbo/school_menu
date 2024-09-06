from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


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

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group

from users.models import User

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, admin.ModelAdmin):
    pass

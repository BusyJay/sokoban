import importlib
import os
import shutil

from django.conf import settings
from django.utils import version
from django.contrib import admin

from sokoban.forms import MiddleWareAdminEditForm
from sokoban.models import Project, MiddleWare, MiddleWareMountOptions
from sokoban.utils import get_middle_ware_connection


__author__ = 'jay'


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'update_time')
    readonly_fields = ('id', 'create_time', 'update_time')
    ordering = ('-create_time', 'update_time')

admin.site.register(Project, ProjectAdmin)


class MiddleWareAdmin(admin.ModelAdmin):
    form = MiddleWareAdminEditForm
    list_display = ('name', 'type', 'author', 'verbose_version', 'update_time')
    ordering = ('-upload_time', '-update_time')

    def verbose_version(self, obj):
        return version.get_version(obj.version)
    verbose_version.allow_tags = True
    verbose_version.short_description = 'version'

    def save_model(self, request, obj, form, change):
        super(MiddleWareAdmin, self).save_model(request, obj, form, change)
        middle_ware = importlib.import_module(obj.name)
        # if it's filter
        if change and hasattr(middle_ware, 'on_upgrade'):
            middle_ware.on_upgrade(get_middle_ware_connection(),
                    form.previous_version)
        elif not change and hasattr(middle_ware, 'on_install'):
            middle_ware.on_install(get_middle_ware_connection())

    def delete_model(self, request, obj):
        try:
            middle_ware = importlib.import_module(obj.name)
            if hasattr(middle_ware, 'on_uninstall'):
                middle_ware.on_uninstall(get_middle_ware_connection())
        except Exception as e:
            # falling silently
            print e
        finally:
            MiddleWareMountOptions.objects.filter(
                middle_ware__id=obj.id).delete()
            super(MiddleWareAdmin, self).delete_model(request, obj)
            middle_ware_root = os.path.join(
                settings.SOKOBAN_MIDDLE_WARE_ROOT, obj.name)
            shutil.rmtree(middle_ware_root)

admin.site.register(MiddleWare, MiddleWareAdmin)


class MiddleWareMountOptionsAdmin(admin.ModelAdmin):
    pass

admin.site.register(MiddleWareMountOptions, MiddleWareMountOptionsAdmin)

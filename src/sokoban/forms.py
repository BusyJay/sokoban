import os
import tarfile
import importlib
import shutil
import logging

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from sokoban.models import Project, MiddleWare
from sokoban.models import Schedule, MiddleWareMountOptions
from sokoban.utils import parse_version_code


__author__ = 'jay'


class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('owner', 'id', 'create_time', 'update_time', 'last_sync_time')


class ProjectBasicForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('owner', 'id', 'name', 'create_time',
                   'update_time', 'last_sync_time')


class ProjectScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        exclude = ('owner', 'update_time', 'attached_job')


class ProjectOptionForm(forms.ModelForm):

    class Meta:
        model = MiddleWareMountOptions
        exclude = ('owner_project',)


class MiddleWareAdminEditForm(forms.ModelForm):
    middle_ware = forms.FileField(label=u'MiddleWare File',
                                  max_length=5242880,  # 5M
                                  help_text=u'Only .smw files are accepted.')

    def clean_middle_ware(self):
        middle_ware_file = super(MiddleWareAdminEditForm, self).clean()
        if 'middle_ware' not in middle_ware_file:
            raise ValidationError(u'Missing required file!!!')
        middle_ware_file = middle_ware_file['middle_ware']
        _, ext = os.path.splitext(middle_ware_file.name)
        if ext.lower() != '.smw':
            raise ValidationError(u'Only .smw file is accepted.')
        try:
            tarball = tarfile.open(fileobj=middle_ware_file, mode="r:bz2")
        except:
            raise ValidationError(u'Invalid middle ware!!!')
        member_names = tarball.getnames()
        if not member_names or not all(member_names):
            raise ValidationError(u'empty middle ware!!!')
        prefix = member_names[0].split('/', 1)[0]
        prefix_dir = prefix + '/'
        if (prefix_dir[0] == '/' or
                any('..' in path or
                    not path.startswith(prefix_dir) and
                    path != prefix for path in member_names)):
            raise ValidationError(u'Evil middle ware!!!')
        # avoid fake module attack
        middle_ware_root = os.path.join(
            settings.SOKOBAN_MIDDLE_WARE_ROOT, prefix)
        module_exists = False
        try:
            middle_ware_module = importlib.import_module(prefix)
            # maybe middle_ware_module has been *uninstall*.
            reload(middle_ware_module)
        except ImportError:
            pass
        else:
            module_exists = True
        # if updating an existing middle ware
        if self.instance.pk:
            self.previous_version = self.instance.version
            shutil.rmtree(os.path.join(settings.SOKOBAN_MIDDLE_WARE_ROOT,
                                       self.instance.name))
        elif module_exists:
            raise ValidationError(u'%s is a reversed.' % prefix)

        try:
            tarball.extractall(settings.SOKOBAN_MIDDLE_WARE_ROOT)

            # I have extend path in setting file
            middle_ware_module = importlib.import_module(prefix)
            middle_ware_module = reload(middle_ware_module)
        except ImportError as e:
            logging.error(e)
            shutil.rmtree(middle_ware_root)
            raise ValidationError(u"Failed to import the the package %s"
                                  % prefix)
        if hasattr(middle_ware_module, 'NetClient'):
            self.instance.type = 4
        elif hasattr(middle_ware_module, 'Filter'):
            self.instance.type = 0
        else:
            shutil.rmtree(middle_ware_root)
            raise ValidationError(u'Invalid middle ware!!!')
        try:
            if 'write' in middle_ware_module.catalog:
                self.instance.type |= 2
            if 'read' in middle_ware_module.catalog:
                self.instance.type |= 1
            self.instance.name = prefix
            self.instance.author = middle_ware_module.__author__
            try:
                parse_version_code(middle_ware_module.__version__)
            except:
                raise ValidationError(u'invalid version code,'
                                      u' you should follow format like'
                                      u' (0, 0, 1, "alpha", 0)!!')
            self.instance.version = middle_ware_module.__version__
        except AttributeError:
            shutil.rmtree(middle_ware_root)
            raise ValidationError(u'Invalid middle ware!!!')
        return middle_ware_file

    def get_previous_version(self):
        try:
            return self.previous_version
        except AttributeError:
            return None

    class Meta:
        model = MiddleWare
        exclude = ('type', 'name', 'author', 'version', 'physical_url',
                   'upload_time', 'update_time')

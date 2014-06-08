import importlib

from django.shortcuts import render
from django.utils import timezone

from sokoban.forms import ProjectCreateForm, ProjectBasicForm
from sokoban.forms import ProjectScheduleForm, ProjectOptionForm
from sokoban.models import Project, MiddleWare, Schedule
from sokoban.models import MiddleWareMountOptions, SyncLog
from sokoban.utils import json_api, must_login, get_middle_ware_connection


__author__ = 'jay'


def index(request):
    return render(request, 'site.html')


def dashboard(request):
    return render(request, 'index.html')


@must_login
def home(request):
    return render(request, 'home.html')


@must_login
@json_api
def list_projects(request, owner):
    if (owner != request.user.username and
            not request.user.has_perm('change_project')):
        return {
            'errors': 'You have no permission to view others project'
        }, 403
    project_list = Project.objects.filter(owner__username=owner)
    project_list = project_list.order_by('-last_sync_time')
    return [{
        'name': project.name,
        'home_page': project.home_page,
        'logo': project.logo,
        'last_sync_time': project.last_sync_time,
        'create_time': project.create_time,
        'update_time': project.update_time,
    } for project in project_list]


def create_project(request):
    if request.method == 'GET':
        return render(request, 'sokoban/project_create.html', dictionary={
            'project_create_form': ProjectCreateForm,
        })

    project_create_form = ProjectCreateForm(request.POST)
    if not project_create_form.is_valid():
        return {
            'errors': project_create_form.errors.as_ul(),
        }, 400
    project = project_create_form.save(commit=False)
    project.owner = request.user
    project.save(force_insert=True)
    return {
        'name': project.name,
        'home_page': project.home_page,
        'logo': project.logo,
        'create_time': project.create_time,
        'update_time': project.update_time,
    }


def ls_basic(user=None, name=None, raw=False, instance=None):
    if not instance:
        instance = Project.objects.filter(name=name,
                                          owner=user).all()
        if instance:
            instance = instance[0]
        else:
            instance = None
    if raw:
        return instance
    if not instance:
        return {
            'errors': 'project has not been created yet.',
        }, 404
    return {
        'name': instance.name,
        'home_page': instance.home_page,
        'logo': instance.logo,
        'create_time': instance.create_time,
        'skip_history': instance.skip_history,
        'log_level':  instance.log_level,
        'update_time': instance.update_time,
        'last_sync_version': instance.last_sync_version,
    }


def update_basic(request, project):
    basic_form = ProjectBasicForm(request.POST, instance=project)
    if not basic_form.is_valid():
        return {
            'errors': basic_form.errors.as_ul(),
        }, 400
    project = basic_form.save(commit=False)
    project.update_time = timezone.now()
    project.save()
    return ls_basic(instance=project)


def ls_schedule(user=None, name=None, raw=False, instance=None):
    if not instance:
        project = ls_basic(user, name, raw=True)
        if not project:
            if raw:
                return None
            return {
                'errors': 'project has not been created yet.',
            }, 404
        try:
            instance = project.schedule
        except Schedule.DoesNotExist:
            project.schedule = Schedule()
            instance = project.schedule
            instance.save()
    if raw:
        return instance
    return {
        'start_time': instance.start_time,
        'interval': instance.interval,
        'status': instance.status,
        'update_time': instance.update_time,
        'next_run': instance.attached_job and instance.attached_job.next_run_time or '',
    }


def update_schedule(request, schedule):
    schedule_form = ProjectScheduleForm(request.POST,
                                        instance=schedule)
    if not schedule_form.is_valid():
        return {
            'errors': schedule_form.errors.as_ul()
        }, 400
    schedule = schedule_form.save(commit=False)
    if schedule.status == 0:
        mount_options = schedule.owner.middlewaremountoptions_set.all()
        # since opt.mount_as only valid in 0, 1, 2, 3, and we make sure
        # none will be repeated.
        if (len(mount_options) != 4 or
                any(opt.middle_ware_id is None for opt in mount_options)):
            return {
                'errors': 'middle mount option is not completed yet,'
                          ' can not start synchronization.',
            }, 400
        schedule.last_sync_time = None
    schedule.update_time = timezone.now()
    schedule.save()
    return ls_schedule(instance=schedule)


# noinspection PyUnresolvedReferences
def ls_option(user=None, name=None, option=None, raw=False, instance=None):
    # TODO disable returning sensitive information
    if not instance:
        project = ls_basic(user, name, raw=True)
        if project:
            instance = project.middlewaremountoptions_set.\
                filter(mount_as=option).select_related().all()
            if instance:
                instance = instance[0]
            else:
                instance = MiddleWareMountOptions()
                instance.mount_as = option
                instance.owner_project_id = project.pk
                instance.save()
    if raw:
        return instance
    if not instance:
        return {
            'errors': 'project not exists!'
        }, 404
    return {
        'middle_ware': instance.middle_ware_id,
        'mount_as': instance.mount_as,
        'options': instance.options or None,
    }


def update_option(request, option):
    option_form = ProjectOptionForm(request.POST, instance=option)
    if not option_form.is_valid():
        return {
            'errors': option_form.errors.as_ul(),
        }, 400
    option = option_form.save(commit=False)
    middle_ware = importlib.import_module(option.middle_ware.name)
    try:
        if hasattr(middle_ware, 'on_bind'):
            option.options = middle_ware.on_bind(
                db=get_middle_ware_connection(), obj=option.options,
                user_id=request.user.pk, project_id=option.owner_project_id)
    except Exception as e:
        return {
            'errors': str(e)
        }, 500
    option.save()
    return ls_option(instance=option)


@must_login
@json_api
def rest_project(request, name, action=None):
    if request.method == 'GET':
        if action == 'details':
            return render(request, 'sokoban/project_details.html', dictionary={
                'project_basic_form': ProjectBasicForm,
            })
        elif action == 'create':
            return render(request, 'sokoban/project_create.html', dictionary={
                'project_create_form': ProjectCreateForm,
            })
        elif action == 'basic':
            return ls_basic(request.user, name)
        elif action == 'schedule':
            return ls_schedule(request.user, name)
        elif action == 'pull':
            return ls_option(request.user, name, 0)
        elif action == 'parse':
            return ls_option(request.user, name, 1)
        elif action == 'inflate':
            return ls_option(request.user, name, 2)
        elif action == 'push':
            return ls_option(request.user, name, 3)
        else:
            return {
                'errors': 'invalid action!',
            }, 400
    elif request.method == 'POST':
        if action == 'basic':
            project = ls_basic(request.user, name, raw=True)
            if not project:
                project = create_project(request)
            else:
                project = update_basic(request, project)
            return project
        elif action == 'schedule':
            schedule = ls_schedule(request.user, name, raw=True)
            return update_schedule(request, schedule)
        else:
            if action == 'pull':
                option_value = 0
            elif action == 'parse':
                option_value = 1
            elif action == 'inflate':
                option_value = 2
            elif action == 'push':
                option_value = 3
            else:
                return {
                    'errors': 'invalid option values',
                }, 400
            option = ls_option(request.user, name, option_value, raw=True)
            return update_option(request, option)
    elif request.method == 'DELETE':
        project = ls_basic(request.user, name, raw=True)
        if not project:
            return {
                'errors': 'project not exists!',
            }, 404
        project.delete()
        return {
            'success': 1,
        }
    else:
        return {
            'errors': 'invalid method',
        }, 400


@must_login
@json_api
def installed_middle_ware(request):
    installed_ware = MiddleWare.objects.all()
    parsed_wares = []
    for ware in installed_ware:
        parsed_ware = {
            "id": ware.pk,
            "name": ware.name,
            "type": ware.type,
            "author": ware.author,
            "version": ware.version,
        }
        model = importlib.import_module(ware.name)
        if callable(model.form):
            parsed_ware["form"] = model.form(
                db=get_middle_ware_connection(), user_id=request.user.pk)
        else:
            parsed_ware["form"] = model.form
        parsed_wares.append(parsed_ware)
    return parsed_wares


def alert_login_required(request):
    return render(request, '403.html')


@must_login
@json_api
def get_log(request, project_name):
    try:
        since = int(request.GET.get('since', '0'))
    except ValueError:
        since = 0
    try:
        limit = int(request.GET.get('limit', '20'))
    except ValueError:
        limit = 20
    if limit > 100 or limit < 0:
        limit = 100
    if since < 0:
        since = 0
    log_set = SyncLog.objects.filter(owner__owner=request.user,
                                     pk__gt=since)
    if project_name is not None:
        log_set = log_set.filter(owner__name=project_name)
    log_set = log_set.order_by('-id')
    log_set = log_set[:limit]
    return [{
        'id': log.id,
        'level': log.level,
        'content': log.content,
        'log_time': log.create_time,
    } for log in log_set]

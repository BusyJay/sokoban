from datetime import timedelta
import uuid

from apscheduler.triggers import IntervalTrigger
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, pre_delete, post_delete
from django.utils import timezone

from scheduler.models import sched, DjangoJob
from sokoban.fields import JsonField


__author__ = 'jay'


LOG_DEBUG = 0
LOG_INFO = 1
LOG_WARNING = 2
LOG_ERROR = 3


LOG_LEVEL = (
# debug level should not be exposed to users.
    (LOG_DEBUG, 'debug'),
    (LOG_INFO, 'info'),
    (LOG_WARNING, 'warning'),
    (LOG_ERROR, 'error'),
)


class Project(models.Model):
    id = models.CharField(max_length=36, primary_key=True,
                          default=lambda: str(uuid.uuid4()))
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, 'uuid',
                              verbose_name=u'Creator')
    name = models.CharField(u'Project Name', max_length=140)
    home_page = models.URLField(u'Project Home', max_length=4096,
                                null=True, blank=True)
    logo = models.URLField(u'Project Logo', max_length=4096,
                           null=True, blank=True)
    skip_history = models.BooleanField(u'Skip History', default=True)
    log_level = models.IntegerField(u'Log Level', choices=LOG_LEVEL,
                                    default=LOG_INFO)

    last_sync_time = models.DateTimeField(u'Last Sync', null=True)
    last_sync_version = models.CharField(u'Last Sync Version', max_length=140,
                                         null=True, blank=True)
    create_time = models.DateTimeField(u'Create Time', auto_now_add=True)
    update_time = models.DateTimeField(u'Update Time', auto_now_add=True)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('owner', 'name')


def delete_project(instance, using, **kwargs):
    from sokoban.sync_worker import clean_project
    clean_project(instance)
    SyncLog.objects.filter(owner__id=instance.id).delete()
    MiddleWareMountOptions.objects.filter(owner_project__id=instance.id).delete()
    Schedule.objects.filter(owner__id=instance.id).delete()


pre_delete.connect(delete_project, sender=Project,
                   dispatch_uid="sokoban.models.delete_project")



MIDDLE_WARE_TYPE = (
    (1, u'In Filter'),
    (2, u'Out Filter'),
    (3, u'Filter'),
    (5, u'In Network Client'),
    (6, u'Out Network Client'),
    (7, u'Network Client'),
)


class MiddleWare(models.Model):
    type = models.IntegerField(u'Type', choices=MIDDLE_WARE_TYPE, default=1)
    name = models.CharField(u'Name', max_length=140)
    author = models.CharField(u'author', max_length=140)
    version = JsonField(u'version', max_length=50)

    upload_time = models.DateTimeField(u'Upload Time', default=timezone.now)
    update_time = models.DateTimeField(u'Update Time',
                                       auto_now=True, auto_now_add=True)

    def __unicode__(self):
        return self.name


MIDDLE_WARE_MOUNT_TYPE = (
    (0, u'Pull - Network Client'),
    (1, u'Pull - Filter'),
    (2, u'Push - Filter'),
    (3, u'Push - Network Client'),
)


class MiddleWareMountOptions(models.Model):
    owner_project = models.ForeignKey(Project, verbose_name=u'Owner Project',
                                      on_delete=models.DO_NOTHING)
    middle_ware = models.ForeignKey(MiddleWare, null=True,
                                    blank=True, verbose_name=u'Middle Ware',
                                    on_delete=models.DO_NOTHING)
    mount_as = models.IntegerField(u'Type', choices=MIDDLE_WARE_MOUNT_TYPE,
                                   default=0)
    options = JsonField(u'Options', null=True, blank=True, max_length=4096)

    update_time = models.DateTimeField(u'Update Time', auto_now=True,
                                       auto_now_add=True)

    def __unicode__(self):
        return self.get_mount_as_display()


PROJECT_SCHEDULE_STATUS = (
    (0, u'Start'),
    (1, u'Stop'),
)


class Schedule(models.Model):
    owner = models.OneToOneField(Project, verbose_name=u"Owner Project",
                                on_delete=models.DO_NOTHING)
    start_time = models.DateTimeField(u"Start Time", default=timezone.now())
    interval = models.IntegerField(u"Interval", help_text=u"In hours",
                                   default=168)  # a week
    status = models.IntegerField(u"Status", choices=PROJECT_SCHEDULE_STATUS,
                                 default=1)

    update_time = models.DateTimeField(u'Update Time', auto_now_add=True)
    attached_job = models.ForeignKey(DjangoJob, null=True, blank=True,
                                    on_delete=models.DO_NOTHING)


# noinspection PyUnusedLocal
def update_schedule(instance, raw, using, update_fields, **kwargs):
    if instance.status == 1:
        if instance.attached_job_id is not None:
            job = instance.attached_job
            instance.attached_job_id = None
            instance.save()
            # in case foreignkey not update
            instance.attached_job = None
            sched.unschedule_job(job)
        return

    from sokoban.sync_worker import sync_project
    if instance.attached_job_id is None:
        interval = timedelta
        job_name = '%s : %s' % (instance.owner.id, instance.owner.name)
        job = sched.add_interval_job(sync_project,
                                     start_date=instance.start_time,
                                     args=(instance.owner_id,),
                                     name=job_name,
                                     hours=instance.interval)
        instance.attached_job_id = job.id
        instance.save()
        sched._wakeup.set()
        return

    interval = timedelta(hours=instance.interval)
    trigger = IntervalTrigger(interval, instance.start_time)
    instance.attached_job.trigger = trigger
    instance.attached_job.compute_next_run_time(timezone.now())
    instance.attached_job.save()
    sched._wakeup.set()


def delete_schedule(instance, using, **kwargs):
    if not instance.attached_job_id:
        return
    job = DjangoJob.objects.filter(id=instance.attached_job_id).get()
    sched.unschedule_job(job)


post_delete.connect(delete_schedule, sender=Schedule,
                   dispatch_uid="sokoban.models.delete_schedule")


pre_save.connect(update_schedule, sender=Schedule,
                 dispatch_uid="sokoban.models.update_schedule")


class SyncLog(models.Model):
    owner = models.ForeignKey(Project, verbose_name=u"Project",
                              on_delete=models.DO_NOTHING)
    level = models.IntegerField(u'Level', choices=LOG_LEVEL)
    content = models.TextField(u'Content')

    create_time = models.DateTimeField(u'Log Time', auto_now_add=True)

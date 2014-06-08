from threading import Lock
import logging
from apscheduler.events import EVENT_SCHEDULER_START, SchedulerEvent, \
    EVENT_SCHEDULER_SHUTDOWN

from apscheduler.job import Job
from apscheduler.jobstores.base import JobStore
from apscheduler.scheduler import Scheduler
from apscheduler.util import obj_to_ref, ref_to_obj, time_difference
from django.db import models, transaction
from django.utils import timezone

from scheduler.fields import PickleField


logger = logging.getLogger(__name__)


@transaction.commit_manually
def flush_transaction():
    """
    Flush the current transaction so we don't read stale data

    by Nick Craig-Wood
    Use in long running processes to make sure fresh data is read from
    the database.  This is a problem with MySQL and the default
    transaction mode.  You can fix it by setting
    "transaction-isolation = READ-COMMITTED" in my.cnf or by calling
    this function at the appropriate moment
    """
    transaction.commit()


class DjangoJob(Job, models.Model):
    trigger = PickleField('job trigger')
    func_ref = models.CharField('function ref', max_length=1024)
    args = PickleField('function args')
    kwargs = PickleField('function kwargs')
    name = models.CharField('job name', max_length=1024)
    misfire_grace_time = models.IntegerField('misfire_grace_time')
    coalesce = models.BooleanField('coalesce')
    max_runs = models.IntegerField('max_runs', null=True, blank=True)
    max_instances = models.IntegerField('max_instances', null=True, blank=True)
    next_run_time = models.DateTimeField('next_run_time')
    runs = models.BigIntegerField('runs')

    def __init__(self, *args, **kwargs):
        if len(args) > 1 and hasattr(args[1], '__call__') or 'func' in kwargs:
            models.Model.__init__(self)
            Job.__init__(self, *args, **kwargs)
        else:
            models.Model.__init__(self, *args, **kwargs)
            self.instances = 0
            self._lock = Lock()
            self.func = ref_to_obj(self.func_ref)

    def compute_next_run_time(self, now):
        # make now real
        return super(DjangoJob, self).compute_next_run_time(timezone.now())


class DjangoStore(JobStore):
    def update_job(self, job):
        job.func_ref = obj_to_ref(job.func)
        job.save()

    def close(self):
        super(DjangoStore, self).close()

    def remove_job(self, job):
        job.delete()

    def load_jobs(self):
        jobs = []
        for django_job in DjangoJob.objects.all():
            jobs.append(django_job)
        return jobs

    def add_job(self, job):
        job.func_ref = obj_to_ref(job.func)
        job.save()

    @property
    def jobs(self):
        flush_transaction()
        return DjangoJob.objects.all()


# TODO: rewrite the whole scheduler to fit django framework
class DjangoScheduler(Scheduler):
    def add_job(self, trigger, func, args, kwargs, jobstore='default',
                **options):
        job = DjangoJob(trigger, func, args or [], kwargs or {},
                        options.pop('misfire_grace_time',
                                    self.misfire_grace_time),
                        options.pop('coalesce', self.coalesce), **options)
        if not self.running:
            self._pending_jobs.append((job, jobstore))
            logger.info('Adding job tentatively -- it will be properly '
                        'scheduled when the scheduler starts')
        else:
            self._real_add_job(job, jobstore, True)
        return job

    def _main_loop(self):
        """Executes jobs on schedule."""

        logger.info('Scheduler started')
        self._notify_listeners(SchedulerEvent(EVENT_SCHEDULER_START))

        self._wakeup.clear()
        while not self._stopped:
            logger.debug('Looking for jobs to run')
            now = timezone.now()
            next_wakeup_time = self._process_jobs(now)

            # Sleep until the next job is scheduled to be run,
            # a new job is added or the scheduler is stopped
            if next_wakeup_time is not None:
                wait_seconds = time_difference(next_wakeup_time, now)
                logger.debug('Next wakeup is due at %s (in %f seconds)',
                             next_wakeup_time, wait_seconds)
                try:
                    self._wakeup.wait(wait_seconds)
                except IOError:  # Catch errno 514 on some Linux kernels
                    pass
                self._wakeup.clear()
            elif self.standalone:
                logger.debug('No jobs left; shutting down scheduler')
                self.shutdown()
                break
            else:
                logger.debug('No jobs; waiting until a job is added')
                try:
                    self._wakeup.wait()
                except IOError:  # Catch errno 514 on some Linux kernels
                    pass
                self._wakeup.clear()

        logger.info('Scheduler has been shut down')
        self._notify_listeners(SchedulerEvent(EVENT_SCHEDULER_SHUTDOWN))

    def _run_job(self, job, run_times):
        naive_rts = (timezone.make_naive(run_time,
                                         timezone.get_current_timezone())
                     for run_time in run_times)
        return super(DjangoScheduler, self).\
            _run_job(job, naive_rts)


sched = DjangoScheduler()

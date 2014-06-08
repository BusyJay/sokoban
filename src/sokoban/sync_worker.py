import os
import fcntl
import time
import errno
import json
import shutil
import importlib
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
import sh

from sokoban import models
from sokoban.utils import get_middle_ware_connection


__author__ = 'jay'


class SyncLogger(object):
    def __init__(self, project):
        self.project = project
        self.level = models.LOG_INFO

    def set_level(self, level):
        self.level = level

    def info(self, content):
        self.log(models.LOG_INFO, content)

    def debug(self, content):
        self.log(models.LOG_DEBUG, content)

    def warning(self, content):
        self.log(models.LOG_WARNING, content)

    def error(self, content):
        self.log(models.LOG_ERROR, content)

    def log(self, level, content):
        if level >= self.level:
            self.project.synclog_set.add(
                models.SyncLog(level=level, content=content))


def get_change_log(git):
    logs = git.diff(cached=True, name_status=True,
                    M=True, oneline=True).split('\n')
    changes = []
    for log in logs:
        log_details = log.split()
        if not log or log_details[-1] == '__meta__.json':
            continue
        change = dict(
            operation=None,
            content_type='page' if log.endswith('.html') else 'attachment',
            path=log_details[1],
            second_path=None
        )
        if log_details[0] == 'A':
            change['operation'] = 'add'
        elif log_details[0] == 'M':
            change['operation'] = 'modified'
        elif log_details[0] == 'D':
            change['operation'] = 'delete'
        elif log_details[0][0] == 'R':
            change['operation'] = 'move'
            change['second_path'] = log_details[2]
        changes.append(change)
    return changes


def get_outline(file_path):
    with open(file_path, 'r') as outline_reader:
        outline = json.load(outline_reader)
    cached = {}

    def travel_outline(cur_outline, up_dir):
        for item in cur_outline:
            for sub_path, sub_outline in item.iteritems():
                if isinstance(sub_outline, list):
                    travel_outline(sub_outline, up_dir + [sub_path])
                cached[sub_path] = tuple(up_dir)

    travel_outline(outline, [])
    return cached


def begin_task(project, conn, logger):
    project.last_sync_time = timezone.now()
    project.save()
    mount_options = project.middlewaremountoptions_set\
        .order_by('mount_as').select_related().all()
    if len(mount_options) != 4:
        logger.error('configuration for project %s is not completed'
                     % project.name)
        if project.schedule:
            project.schedule.status = 1
            project.schedule.save()
        return
    logger.info('initializing middle ware...')
    logger.info('inflate a checkout client...')
    pull_module = importlib.import_module(
        mount_options[0].middle_ware.name)
    pull = pull_module.NetClient(form=mount_options[0].options, logger=logger,
                                 project_id=project.id, db=conn)
    logger.info('inflate a read filter...')
    parse_module = importlib.import_module(
        mount_options[1].middle_ware.name)
    parse = parse_module.Filter(project_id=project.id, db=conn,
                                logger=logger, read_client=pull,
                                form=mount_options[1].options)
    logger.info('inflate a push client...')
    push_module = importlib.import_module(
        mount_options[3].middle_ware.name)
    push = push_module.NetClient(form=mount_options[3].options, logger=logger,
                                 project_id=project.id, db=conn)
    logger.info('inflate a write makeup...')
    inflate_module = importlib.import_module(
        mount_options[2].middle_ware.name)
    inflate = inflate_module.Filter(project_id=project.id, db=conn,
                                    logger=logger, write_client=push,
                                    form=mount_options[2].options)
    logger.info('setup environment...')
    working_root = os.path.join(settings.SOKOBAN_WORKING_DIRECTORY,
                                project.id)
    working_tree_root = os.path.join(
        settings.SOKOBAN_WORKING_TREE_DIRECTORY, project.id)
    core_vcs_root = os.path.join(settings.SOKOBAN_VCS_DIRECTORY, project.id)
    outline_path = os.path.join(working_tree_root, '__meta__.json')
    # noinspection PyUnresolvedReferences
    git = sh.git.bake(_tty_out=False, git_dir=core_vcs_root)
    if not os.path.exists(core_vcs_root):
        git.init(bare=True)
    git = git.bake(work_tree=working_tree_root)
    if not project.last_sync_version and project.last_sync_version is not 0:
        logger.info('it seems we have never sync %s before, '
                    'will start from scratch' % project.name)
    else:
        logger.info('start synchronization from version %s'
                    % project.last_sync_version)
    i = 0
    for per_merge in parse.merge_step(
            working_tree_root, last_version=project.last_sync_version,
            working_directory=working_root, virtual_build=virtual_build,
            skip_history=project.skip_history):
        git.add(all=True)
        change_logs = get_change_log(git)
        if not change_logs:
            logger.info('nothing change to core vcs, skip...')
            project.last_sync_version = per_merge['version']
            continue
        logger.info('merging the %s changes...' % i)
        author = "%s <%s>" % (per_merge['author'], per_merge['email'])
        date = per_merge['date'].isoformat()
        message = per_merge['commit_message']
        outline = get_outline(outline_path)
        conn.begin()
        try:
            inflate.apply(working_tree_root, outline, change_logs)
            conn.commit()
        except:
            conn.rollback()
            raise
        git.commit(author=author, date=date, message=message)
        project.last_sync_version = per_merge['version']
        i += 1
    project.last_sync_version = pull.get_version()
    if i:
        logger.info('%s commits have been merged' % i)
    else:
        logger.info('no merging needed!')


def virtual_build(project_root, working_root, lang, build_command, logger):
    """build docs in a virtual environment.

    :param project_root: root directory of target project
    :param working_root: relative path to working directory that build
     command should run in.
    :param lang: language of the project
    :param build_command: command to build docs.
    :return:
    """
    # noinspection PyUnresolvedReferences
    docker = sh.docker
    mount_point = '/mnt/'
    build_command_path = os.path.join(working_root, str(uuid4()) + '.sh')
    src_command_path = os.path.join(project_root, build_command_path)
    with open(src_command_path, 'w') as fwriter:
        fwriter.write(build_command)
    os.chmod(src_command_path, 0755)
    mapped_command_path = os.path.join(mount_point, build_command_path)
    wd = os.path.join(mount_point, working_root)
    docker_run = docker.bake('run', d=True, w=wd, user='sokoban',
                             volume=':'.join((project_root, mount_point)))
    container_id = docker_run(settings.VIRTUAL_CONTAINER,
                              '--lang', lang, mapped_command_path)
    container_id = container_id.strip()
    run_time = 1
    logger.info('start building the docs...')
    try:
        while container_id in docker.ps(q=True, no_trunc=True).split():
            if run_time >= 14400:  # about an hour
                docker.kill(container_id)
                raise Exception("Build time too long(over an hour)")
            run_time += 1
            time.sleep(0.25)
        logger.debug('building log: %s' % docker.logs(container_id))
        # noinspection PyUnresolvedReferences
        if ' Exit 0 ' not in sh.grep(docker.ps(a=True), container_id[:5]).strip():
            raise Exception("Docs build failed!")
    finally:
        docker.rm(container_id)


def sync_project(project_id):
    try:
        project = models.Project.objects.filter(id=project_id).get()
    except models.Project.DoesNotExist:
        raise KeyError('Cannot find the specified project!!!')
    lock_dir = settings.SYNCHRONIZATION_LOCK_DIR
    if not os.path.exists(lock_dir):
        os.mkdir(lock_dir, 0700)
    lock_file = os.path.join(lock_dir, project_id + '.lock')
    task_lock = open(lock_file, 'w')
    try:
        fcntl.flock(task_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        task_lock.close()
        if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
            try:
                task_begin = time.ctime(os.path.getmtime(lock_file))
            except OSError:
                task_begin = 'unknown time, maybe just finished?'
            raise Exception(
                'Previous task (start at %s) is still running' % task_begin)
        else:
            raise Exception(
                'unable to lock the task, contact administrator please.')
    logger = SyncLogger(project)
    logger.set_level(project.log_level)
    logger.info('begin synchronizing project %s...' % project.name)
    conn = get_middle_ware_connection()
    try:
        begin_task(project, conn, logger)
        logger.info('done.')
    except Exception as e:
        logger.error('catch exception %s' % str(e))
        logger.error('synchronization of %s abort!' % project.name)
        raise
    finally:
        fcntl.flock(task_lock, fcntl.LOCK_UN)
        task_lock.close()
        project.save()
        conn.close()
    if project.schedule.attached_job.next_run_time:
        logger.info('next run at %s' % project.schedule.attached_job.next_run_time)


def clean_project(project):
    conn = get_middle_ware_connection()
    for mw in project.middlewaremountoptions_set.all():
        # noinspection PyBroadException
        try:
            mw_module = importlib.import_module(mw.name)
            mw_module.on_project_delete(conn, project.id)
        except:
            continue
    conn.close()
    working_root = os.path.join(settings.SOKOBAN_WORKING_DIRECTORY,
                                project.id)
    working_tree_root = os.path.join(
        settings.SOKOBAN_WORKING_TREE_DIRECTORY, project.id)
    core_vcs_root = os.path.join(settings.SOKOBAN_VCS_DIRECTORY, project.id)
    shutil.rmtree(working_root, True)
    shutil.rmtree(working_tree_root, True)
    shutil.rmtree(core_vcs_root, True)


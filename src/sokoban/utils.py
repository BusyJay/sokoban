import json
from MySQLdb import cursors
import MySQLdb
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
import fcntl
import functools

__author__ = 'jay'


def json_api(func):
    """Simple decorator that wrap non http response to json

    :param func:
    :return:
    """
    def process_request(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, HttpResponse):
            return result
        status, response = 200, result
        if isinstance(result, tuple):
            response = result[0]
            if len(result) > 1:
                status = result[1]
        json_str = json.dumps(response, cls=DjangoJSONEncoder)
        json_res = HttpResponse(
            content=json_str,
            content_type='application/json',
            status=status,
        )
        return json_res
    return process_request


must_login = login_required(login_url='/403/')


def contab_permission_required(permission, io_key=None):
    def _decorator(func, ):
        def _inner(*args, **kwargs):
            crontab_file = settings.SOKOBAN_CRONTAB_FILE
            open_flag = 'r'
            if permission & fcntl.LOCK_EX:
                open_flag += 'w'
            cron_io = open(crontab_file, open_flag)
            # just let you know, following may blocks
            fcntl.flock(cron_io, permission)
            try:
                if io_key:
                    kwargs[io_key] = cron_io
                return func(*args, **kwargs)
            finally:
                fcntl.flock(cron_io, fcntl.LOCK_UN)
                cron_io.close()
        return _inner
    return _decorator


contab_read = functools.partial(contab_permission_required, fcntl.LOCK_SH)
contab_write = functools.partial(contab_permission_required, fcntl.LOCK_EX)



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


def get_middle_ware_connection():
    # TODO use database pool instead
    db_settings = settings.DATABASES['sokoban_middle_ware']
    mysql_settings = {}
    if db_settings['HOST'] and db_settings['HOST'][0] == '/':
        mysql_settings['unix_socket'] = db_settings['HOST']
    else:
        mysql_settings['host'] = db_settings['HOST']
    if db_settings['PORT']:
        mysql_settings['port'] = int(db_settings['PORT'])
    mysql_settings['user'] = db_settings['USER']
    mysql_settings['charset'] = 'utf8'
    mysql_settings['passwd'] = db_settings['PASSWORD']
    mysql_settings['db'] = db_settings['NAME'] or 'sokoban_middle_ware'
    mysql_settings['cursorclass'] = cursors.DictCursor
    conn = MySQLdb.connect(**mysql_settings)
    return conn


def parse_version_code(version):
    parsed_version = ['.'.join(map(str, version[:3])), ]
    if len(version) > 3:
        parsed_version.append(str(version[3][:1]).lower())
    if len(version) > 4:
        parsed_version.append(str(version[4]))
    return ''.join(parsed_version)

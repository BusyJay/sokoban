"""A filter that parse documentation from confluence and enhance documentation to confluence.
"""
import contextlib


__author__ = 'jay'
__version__ = (0, 0, 1, 'alpha', 0)

catalog = ['write']

from main import Filter

__all__ = ['Filter']


form = None


def on_install(db):
    """will be execute when installed.

    raise any exception to revert the installation.
    :param db: a database connection used for creating its tables if needed
    """
    with contextlib.closing(db.cursor()) as c:
        c.execute("set sql_notes=0")
        c.execute("create table if not exists resources ("
                  "id int(11) primary key auto_increment,"
                  "res_type varchar(10) not null,"  # should be 'page' or 'attachment'
                  "path varchar(255) not null,"  # relative path of resources base on work root
                  "project varchar(255) not null"
                  ")")
        c.execute("create table if not exists pages ("
                  "oid int(11) primary key,"
                  "parent_id int(11) default null,"
                  "resource_id int(11) not null references resources(id),"
                  "title varchar(255) not null,"
                  "postfix varchar(256) default null,"
                  "version int(11) default 0,"
                  "create_time timestamp"
                  ")")
        c.execute("create table if not exists attachments ("
                  "oid int(11) primary key,"
                  "parent_id int(11) not null references pages(id) ON DELETE CASCADE,"
                  "resource_id int(11) not null references resources(id),"
                  "resource_name varchar(256) not null,"
                  "create_time timestamp"
                  # following key is removed because it's too large.
                  # but should be checked during operation.
                  # "unique key (parent_id, resource_name)"
                  ")")
        c.execute("set sql_notes=1")


def on_upgrade(db, pre):
    """will be execute when upgrade.

    raise any exception to revert the upgrade.
    :param db:
    :param pre: previous version code
    :return:
    """
    on_install(db)


def on_uninstall(db):
    """will be execute when uninstalled.

    no matter what happened, the plugin will be removed eventually.
    """
    with contextlib.closing(db.cursor()) as c:
        c.execute("drop table attachments")
        c.execute("drop table pages")
        c.execute("drop table resources")


def on_project_delete(db, project_id):
    with contextlib.closing(db.cursor()) as c:
        c.execute("delete from attachments "
                  "join resources on attachments.resource_id=resources.id "
                  "where resources.project=%s", project_id)
        c.execute("delete from pages "
                  "join resources on pages.resource_id=resources.id "
                  "where resources.project=%s", project_id)
        c.execute("delete from resources "
                  "where resources.project=%s", project_id)
    db.commit()


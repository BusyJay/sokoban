import contextlib
from datetime import datetime
from functools import partial
import os
import parser


__author__ = 'jay'


def get_page_by_href(href, cursor, path=None, tracker=None, project_name=None):
    if '#' in href:
        href = href[:href.index('#')]
    if '?' in href:
        href = href[:href.index('?')]
    href = os.path.join(os.path.dirname(path), href)
    href = os.path.normpath(href)
    cursor.execute("select * from resources "
                   "join pages on resources.id=pages.resource_id "
                   "where resources.res_type='page' && path=%s && project=%s",
                   (href, project_name))
    target = cursor.fetchone()
    page = {}
    if target:
        page.update(target)
        if target['postfix']:
            page['title'] = add_postfix_to_title(
                page['title'], page['postfix'])
    if tracker is not None:
        tracker.add(path)
    return page


def add_postfix_to_title(page_title, postfix):
    if isinstance(page_title, unicode):
        page_title = page_title.encode('utf-8')
    if isinstance(postfix, unicode):
        postfix = postfix.encode('utf-8')
    return str(page_title) + ' - ' + str(postfix)


def remove_postfix(page_title, postfix):
    if isinstance(postfix, unicode):
        postfix = postfix.encode()
    return page_title[:page_title.rindex(' - ' + str(postfix))]


def update_page(page_handle, attach_handle, page, source_path, wc, logger):
    with open(source_path, 'r') as reader:
        soup = parser.ConfluencePageInflater(reader, page_handle,
                                             attach_handle)
    page_title = soup.title
    postfix_added = False
    if page['oid'] and page['postfix'] and page['title'] == page_title:
        page_title = add_postfix_to_title(page_title, page['postfix'])
        postfix_added = True
    is_home_page = soup.is_home_page
    keep_trying = True
    while keep_trying:
        if not page['oid']:
            message = "trying create page with title %s" % page_title
        else:
            message = "trying to modify page [%s:%s] with title %s" % (
                page['oid'], page['version'], page_title)
        logger.info(message)
        try:
            page_info = wc.register_page(
                page_title, soup.cleaned_src, pid=page['oid'],
                parent_id=page['parent_id'], mark_home=is_home_page,
                version=page['version'])
            page['oid'] = page_info[0]
            page['version'] = page_info[1]
            break
        except wc.OperationError:
            # maybe version not right, let's try again
            try:
                page_info = wc.get_page(pid=page['oid'], title=page_title)
            except wc.OperationError:
                page_info = None
            if page_info:
                if page['oid']:
                    if page_info[1] != page['version']:
                        logger.error(
                            "failed.\n"
                            "updated page version [%s] and try again"
                            % page_info[1])
                        page['version'] = page_info[1]
                    else:
                        logger.error("fatal problem, will panic.")
                        raise
                elif not postfix_added and page['postfix']:
                    logger.warning(
                        'page with title %s exists, will try create new page'
                        ' with postfix %s' % (page_title,
                                              str(page['postfix'])))
                    page_title = add_postfix_to_title(page_title,
                                                      page['postfix'])
                    postfix_added = True
                else:
                    logger.error('page with title %s exists!!!' % page_title)
                    raise
            else:
                if page['oid']:
                    logger.warning("It seems that remote page has been"
                                   " deleted, lets create a new one...")
                    page['oid'], page['version'] = None, None
                else:
                    logger.error("fatal problem, let's panic.")
                    raise
    if postfix_added:
        page['title'] = remove_postfix(page_title, page['postfix'])
    else:
        page['title'] = page_title
        page['postfix'] = None
    return page


class Filter(object):
    """filter tags and revert

    A filter should work like follow:

    clean up pages:
    process content -> clean up unneeded tags and attributes -> format -> pass to result

    add or modified pages:
                                           not found
    process content -> search attachment  ---------->  create full page      ->      update database
                           |found                                                            |
                           -> create blank page -> upload attachment -> format link -> modified full page

    add attachment: see above

    modified attachment:
    search references -> update all reference -> update database

    delete content:
           page
    delete ----> delete page -----> update database
             | attachment                      |
             -> search references -> delete all reference

    move content: dismiss
    """

    def __init__(self, project_id, db, logger,
                 write_client=None, form=None, **kwargs):
        """

        :param project_id:
        :param db: a database connection. You should be aware that db should
         produce a cursor type that return result as dict.
        :param logger:
        :param write_client:
        :param form:
        :return:
        """
        if not write_client:
            raise ValueError('write_client should not be None!')
        self.project_name = project_id
        self.wc = write_client
        self.db = db
        self.need_update = set()
        self.form = form
        self.logger = logger

    def _put_page(self, cursor, working_dir, page, tracker=None):
        """put a page with client

        :param cursor:
        :param working_dir: path of source, where can actually read source.
            if None, just create a blank page.
        :param page: page info
        :param tracker: a tracker record the page that unable to be update
         complete this time.
        :return:
        """
        source_path = os.path.join(working_dir, page['path'])

        need_update = True
        if not page['oid']:
            need_update = set()

            def do_nothing(*args):
                need_update.add(args[0])

            page = update_page(
                partial(get_page_by_href, path=page['path'], tracker=tracker,
                        cursor=cursor, project_name=self.project_name),
                do_nothing, page, source_path, self.wc, self.logger)
            cursor.execute('insert into resources values(%s, %s, %s, %s)',
                           (None, 'page', page['path'], self.project_name))
            assert cursor.lastrowid > 0
            cursor.execute("insert into pages values(%s, %s, %s, %s, %s,"
                           " %s, %s)",
                           (page['oid'], page['parent_id'], cursor.lastrowid,
                            page['title'], page['postfix'], page['version'],
                            datetime.utcnow()))
        if need_update:
            oid = page['oid']
            page = update_page(
                partial(get_page_by_href, path=page['path'], tracker=tracker,
                        cursor=cursor, project_name=self.project_name),
                partial(self.get_attach_by_href, page_id=page['oid'],
                        base_path=page['path'], cursor=cursor,
                        working_dir=working_dir),
                page, source_path, self.wc, self.logger)
            cursor.execute("update pages set oid=%s, version=%s, title=%s "
                           "where oid=%s", (page['oid'], page['version'],
                                            page['title'], oid))
        return page['oid'], page['version']

    def apply(self, base_dir, outline, changes):
        """push logs to remote

        :param base_dir:
        :param outline: outline of menu, should follow the format {
            phisical_path: list_of_menu_inheritance,
            ...
        }
        :param changes: should follow the format [{
            'operation': operation,  # 'add', 'modified', 'delete' or 'move'
            'content_type': content_type,  # 'page' or 'attachment'
            'path': path,  # path to documentation
            'second_path': second_path,  #  if operation is 'move', this field
            means target_path, else this field is optional.
        }, ...]
        """
        for change_type in ('delete', 'add', 'modified'):
            target_changes = tuple(
                (c['content_type'], c['path'], c['second_path'])
                for c in changes if c['operation'] == change_type)
            if not target_changes:
                continue
            try:
                handle = getattr(self, 'apply_' + change_type)
            except AttributeError:
                continue  # well, fall silently
            try:
                self.db.begin()
                handle(base_dir, outline, target_changes)
                self.db.commit()
            except:
                self.db.rollback()
                raise

    # noinspection PyUnusedLocal
    def apply_delete(self, base_dir, outline, changes):
        """apply delete action on changes

        :param base_dir:
        :param outline:
        :param changes: should follow the format
         [(content_type, path, second_path), ...].
        :return:
        """
        self.logger.info('applying delete changes...')
        attach_changes = tuple(c for c in changes if c[0] == 'attachment')
        page_changes = tuple(c for c in changes if c[0] == 'page')
        with contextlib.closing(self.db.cursor()) as c:
            for change in attach_changes:
                c.execute("select * from resources "
                          "right join attachments"
                          " on resources.id=attachments.resource_id "
                          "where res_type=%s && path=%s && project=%s",
                          ('attachment', change[1], self.project_name))
                attachments = c.fetchall()
                if not attachments:
                    continue  # maybe something we don't care
                for attach in attachments:
                    self.logger.info('deleting attachment: [%s] %s' % (
                        attach['parent_id'], attach['resource_name']))
                    self.wc.delete_attachment(attach['parent_id'],
                                              attach['resource_name'])
                c.execute("delete from attachments where resources_id=%s",
                          (attach['resource_id'],))
                c.execute("delete from resources where id=%s",
                          (attach['resource_id'],))
            for change in page_changes:
                c.execute("select * from resources "
                          "join pages on resources.id=pages.resource_id "
                          "where res_type=%s && path=%s && project",
                          ('page', change[1], self.project_name))
                res = c.fetchone()
                if not res:
                    continue
                self.logger.info(
                    'deleting page: [%s] %s' % (res['oid'], res['title']))
                self.wc.delete_page(res['oid'])
                c.execute("delete from pages where oid=%s", (res['oid'],))
                c.execute("delete from resources where id=%s",
                          (res['resource_id'],))
        self.logger.info('success applying delete.')

    def get_attach_by_href(self, href, title, cursor, base_path=None,
                           page_id=None, working_dir=None):
        """return attachment referenced by href.

         If not exits, will try to create one.
        :param href:
        :param title:
        :param base_path:
        :param page_id:
        :param cursor:
        :param working_dir:
        :return:
        """
        if not page_id:
            return None
        if '#' in href:
            href = href[:href.index('#')]
        if '?' in href:
            href = href[:href.index('?')]
        href = os.path.join(os.path.dirname(base_path), href)
        href = os.path.normpath(href)

        def get_attach():
            cursor.execute("select * from resources "
                           "join attachments "
                           "on resources.id=attachments.resource_id "
                           "where resources.res_type='attachment' "
                           "&& path = %s && parent_id=%s && project=%s",
                           (href, page_id, self.project_name))
            return cursor.fetchone()

        attach = get_attach()
        if attach:
            return attach
        source_path = os.path.join(working_dir, href)
        file_name = href.replace('/', '_')
        try:
            with open(source_path, 'r') as img_reader:
                aid = \
                    self.wc.register_attachment(img_reader,
                                                page_id, file_name)[0]
                self.logger.info(
                    'added a new attachment to page %s: [%s] %s' % (
                        page_id, aid, file_name))
        except IOError:
            return None
        # noinspection PyBroadException
        try:
            cursor.execute("insert into resources values(%s, %s, %s, %s)",
                           (None, 'attachment', href, self.project_name))
            assert cursor.lastrowid > 0
            res_id = cursor.lastrowid
        except:
            # I guess it's because of Duplicate entry. I don't catch
            #  IntegrityError here because no database type is assumed
            cursor.execute("select id from resources "
                           "where path=%s && project=%s",
                           (href, self.project_name))
            res_id = cursor.fetchone()
            if not res_id:
                raise Exception('insert new resources %s fail' % href)
            res_id = res_id['id']

        cursor.execute("insert into attachments values(%s, %s, %s, %s, %s)",
                       (aid, page_id, res_id, file_name, datetime.now()))
        attach = get_attach()
        return attach

    def apply_add(self, base_dir, outline, changes):
        """apply put action on changes

        put action will create a new page if referenced one does not exist.
        only support single parent mode currently.
        :param base_dir:
        :param outline:
        :param changes:
        :return:
        """
        self.logger.info('applying add changes...')
        page_changes = list(c[1] for c in changes if c[0] == 'page')
        tracker = set()  # used to track page not updated completely

        def loop_back(path, c, level, force_update=False):
            c.execute("select * from resources "
                      "join pages on pages.resource_id=resources.id "
                      "where res_type=%s && path=%s && project=%s",
                      ('page', path, self.project_name))
            cur_page = cursor.fetchone()
            if not cur_page:
                dependency = outline.get(path, None)
                if dependency:
                    parent_page = loop_back(dependency[-1], c, level + 1)
                    cur_page = dict(
                        oid=None,
                        version=None,
                        parent_id=parent_page['oid'],
                        path=path,
                        postfix=path,
                    )
                else:
                    cur_page = dict(
                        oid=None,
                        version=None,
                        parent_id=None,
                        path=path,
                        postfix=path,
                    )
                self.logger.info("Can't find registered page with path %s,"
                                 " will create one." % path)
                cur_page['oid'], cur_page['version'] = self._put_page(
                    c, base_dir, cur_page, tracker)
                page_changes.remove(path)
            elif force_update:
                cur_page['oid'], cur_page['version'] = self._put_page(
                    c, base_dir, cur_page, tracker)
                page_changes.remove(path)
            return cur_page

        with contextlib.closing(self.db.cursor()) as cursor:
            clean_outline = set()
            for outline_path in outline:
                if '#' in outline_path:
                    outline_path = outline_path[:outline_path.index('#')]
                if '?' in outline_path:
                    outline_path = outline_path[:outline_path.index('?')]
                clean_outline.add(outline_path)
            # after this loop, all new pages should be created.
            while page_changes:
                page_path = page_changes[-1]
                # we only care about page listed in outline
                if page_path in clean_outline:
                    loop_back(page_path, cursor, 1)
                if page_changes and page_path == page_changes[-1]:
                    page_changes.pop()
            page_changes, tracker = list(tracker), set()
            # after this loop, all possible missing link should be filled.
            while page_changes:
                page_path = page_changes[-1]
                loop_back(page_path, cursor, 1, force_update=True)
        self.logger.info('success applying add.')

    def apply_modified(self, base_dir, outline, changes):
        self.logger.info('applying modified changes...')
        page_changes = tuple(c[1] for c in changes if c[0] == 'page')
        with contextlib.closing(self.db.cursor()) as cursor:
            sql = "select path from resources" \
                  " where project=%s && res_type=%s && path in (%s"
            if len(page_changes) == 1:
                sql += ')'
            else:
                # question: does a sql statement has a length limit?
                sql = ','.join((sql,) +
                               ('%s',) * (len(page_changes) - 2) + ('%s)',))
            args = (self.project_name, 'page') + page_changes
            cursor.execute(sql, args)
            in_path = set(c['path'] for c in cursor.fetchall())
            add_path = set(page_changes) - in_path
            if add_path:
                # in case we start merging from middle
                self.apply_add(base_dir, outline, add_path)
            for page_path in page_changes:
                cursor.execute("select * from resources "
                               "join pages on pages.resource_id=resources.id "
                               "where res_type=%s && path=%s && project=%s",
                               ('page', page_path, self.project_name))
                cur_page = cursor.fetchone()
                assert cur_page is not None
                self._put_page(cursor, base_dir, cur_page, None)
        self.logger.info('success applying modified.')

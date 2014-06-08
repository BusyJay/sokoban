import json
import os
import re
import tempfile
import functools
import shutil

from bs4 import BeautifulSoup

from parser import RawHtmlParser


__author__ = 'jay'


def test_valid_navigation_menu(ul):
    if ul.name != 'ul':
        return False
    for li in ul.find_all('li'):
        a = li.find('a')
        if a and '//' not in a.attrs.get('href', ''):
            return True
    return False


class Filter(object):
    def __init__(self, project_id, db, logger,
                 read_client=None, form=None, **kwargs):
        """A simple filter design for docs generated for sphinx.

        :param project_id:
        :param db: a database connection.
        You should be aware that db should produce a cursor type that return
         result as dict.
        :param logger:
        :param read_client:
        :param form:
        :return:
        """
        if not read_client:
            raise ValueError('read_client should not be None!')
        self.project_name = project_id
        self.rc = read_client
        self.db = db
        self.logger = logger
        self.need_update = set()
        self.project_docs_root = form['docs_root']
        self.lang = form['lang']
        try:
            self.trigger_pattern = re.compile(
                str(form.get('trigger_pattern', '.*')))
        except re.error as e:
            raise ValueError('pattern not valid: %s' % e.message)
        self.build_working_dir = form.get('working_dir', '.')
        self.build_command = form.get('build_command', None)
        self.shut_up = form['ignore_errors']

    def merge(self, *args, **kwargs):
        return list(self.merge_step(*args, **kwargs))

    def merge_step(self, core_docs_tree, working_directory=None,
                   last_version=None, virtual_build=None,
                   skip_history=True):
        """merge the remote differences into doc version control

        :param core_docs_tree: working root for docs. All changes will
         be cleaned up and update to that directory.
        :param last_version: just merge changes since when. if not specify,
         will merge all changes.
        :param working_directory: if not specify, temporary directory
         of system will be used.
        :param virtual_build: function that will build docs in virtual
         environment.
        :param skip_history: whether sync the historical version of docs
        :return:
        """
        if not working_directory:
            working_directory = tempfile.gettempdir()
        vcs_path = os.path.join(working_directory, self.project_name)
        checkout_path = os.path.join(working_directory,
                                     "%s_ct" % self.project_name)

        def checkout_docs(checkout_version, change_info):
            rc.copy_file(None, checkout_path, checkout_version)
            try:
                virtual_build(checkout_path, self.build_working_dir, self.lang,
                              self.build_command, self.logger)
            except:
                if not self.shut_up:
                    raise
            src_root = os.path.join(checkout_path,
                                    self.project_docs_root)
            if self.filter_docs('index.html', src_root, core_docs_tree):
                return dict(
                    author=change_info['author'],
                    email=change_info['email'],
                    date=change_info['date'],
                    version=change_info['version'],
                    commit_message=change_info['commit_message'],
                )
        with self.rc.open_project(vcs_path) as rc:
            rc.update_project()
            if skip_history:
                version = rc.get_version()
                change = rc.get_change_log(max_count=1, reverse=False)
                change = checkout_docs(version, change[0])
                if change:
                    yield change
                return
            for change in rc.get_lazy_change_log(begin_pos=last_version):
                self.logger.info('checking version %s' % change['version'])
                if all(not self.trigger_pattern.match(c[-1]) and
                        (c[0] != 'move' or
                            not self.trigger_pattern.match(c[1]))
                       for c in change['changed_files']):
                    self.logger.info('skiped for nothing changed to docs')
                    continue
                change = checkout_docs(change['version'], change)
                if change:
                    yield change

    def filter_docs(self, outline_file, source_dir, output_dir):
        """Read documentation structure from outline_file, and convert
         to core_storage compatible version and save to output_dir.

        :param outline_file: relative path to outline file
        :param source_dir: path to source root
        :param output_dir: where to store production
        """
        docs_outline = [{
            outline_file: []
        }]

        outline_file_path = os.path.join(source_dir, outline_file)
        outline_file_dir = os.path.dirname(outline_file_path)
        try:
            with open(outline_file_path, 'r') as fin:
                outline_soup = BeautifulSoup(fin, 'html5lib')
        except IOError:
            return False
        # the first section is usually talking about structure.
        navigation_menus = []
        for section in outline_soup.find_all(class_='section'):
            if section.find(class_='section'):
                continue
            nav = section.find(test_valid_navigation_menu)
            if nav:
                navigation_menus.append(nav)
        if not navigation_menus:
            return False

        def must_handle(base, href):
            if href.startswith('#'):
                return True
            if '//' in href:
                schema = href.split('//', 1)[0]
                return schema in ('http:', 'ftp:', 'https:', '')
            if ':' in href:
                schema = href.split(':', 1)[0]
                return schema == 'mailto'
            href = href.split('?', 1)[0]
            href = href.split('#', 1)[0]
            abs_path = os.path.join(os.path.dirname(base), href)
            abs_path = os.path.normpath(abs_path)
            if abs_path.startswith('..') or not os.path.exists(abs_path):
                if self.shut_up:
                    return True
                else:
                    raise ValueError('file %s not found!!!' % href)
            generate_resource(abs_path)
            return True

        checked = set()

        # magic~
        makedir = lambda path: (os.path.exists(path) or
                                makedir(os.path.dirname(path)) and
                                os.mkdir(path) is None)

        def generate_resource(page):
            if page in checked:
                return
            checked.add(page)
            output_path = os.path.join(output_dir, os.path.relpath(page,
                                                                   source_dir))
            output_path_dir = os.path.dirname(output_path)
            makedir(output_path_dir)
            must_handle_with_base = functools.partial(must_handle, page)
            if page.endswith('.html'):
                with open(output_path, 'w') as writer, \
                    RawHtmlParser(must_handle_with_base) as raw_filter,\
                        open(page, 'r') as reader:
                    raw_filter.feed(reader.read())
                    shutil.copyfileobj(raw_filter, writer)
            else:
                shutil.copyfile(page, output_path)

        def handle_menu(menu, menu_structure):
            for sub_menu in menu.findChildren('li'):
                href = sub_menu.a['href']
                if '//' in href:
                    schema = href.split('//', 1)
                    if schema not in ('http:', 'ftp:', 'https:', ''):
                        if self.shut_up:
                            continue
                        else:
                            raise ValueError('schema %s not allowed!' % href)
                else:
                    abs_href = os.path.normpath(
                        os.path.join(outline_file_dir, href))
                    if os.path.relpath(abs_href, source_dir).startswith('..'):
                        if self.shut_up:
                            abs_href = '#'
                        else:
                            raise ValueError('illegal path: %s!!!' % href)
                    if '#' in abs_href:
                        abs_href = abs_href[:abs_href.index('#')]
                    if not os.path.exists(abs_href):
                        if self.shut_up:
                            abs_href = '#'
                        else:
                            raise ValueError('file %s not found!!!' % href)
                    else:
                        generate_resource(abs_href)
                child_menu = sub_menu.findChild('ul')
                if child_menu:
                    menu_structure.append({href: []})
                    handle_menu(child_menu, menu_structure[-1][href])
                else:
                    menu_structure.append({href: None})

        generate_resource(outline_file_path)
        for nav in navigation_menus:
            handle_menu(nav, docs_outline[0][outline_file])
        with open(os.path.join(output_dir, '__meta__.json'), 'wb') as f_out:
            # well, this file will be put into version control too.
            # so be pretty is better for reading and tracing.
            json.dump(docs_outline, f_out, indent=0)
        return True

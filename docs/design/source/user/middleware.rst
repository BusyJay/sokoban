.. _middleware:

Middle Ware
===========

Introduction
------------

A middle ware is a python package that provides functionality to communicate
with remote hosts or deal with documentations.

For example, I want to use sokoban to synchronize documentations of my python
project from git repo to confluence. So, sokoban will read documentation from
git repo(or clone to be specifically), then generate the documentation and
filter some unexpected tag like script and so on. Let's call the documentation
we get here as *essence*. To track the documentation changes and generate
reports, sokoban will commit *essence* to *essence vcs*. In order To write to
confluence, sokoban need to adjust the tag of essence to make sure they will
fit the requirement of confluence. And finally, sokoban will use rest api of
confluence to write the result to remote.

If the task is just that simple, all we need to do is write the functionality
directly to sokoban. However, we want sokoban not only can sync docs from
git repo, but also mercurial or svn repo. And we may use WikiMedia to
maintain our documentation. So we introduce middle ware here. We write the
specific functionality into a python module, and sokoban will be able to
*plug and play*.

Specification
-------------

There are four different types of middle wares, checkout client, read filter,
write markup, push client. In the example we talked above, checkout client
is used to clone repo. Read filter will filter unexpected tag and reformat
the file to meet *core storage spec*. Then write markup adjust the essence,
use push client to write to remote.

As we said, a middle ware is a python package. Different type of middle ware
has different requirement to the structure of package. But there are some
in common.

common
``````

* middle ware should be *one and only one* python package;
* middle ware should be release as a compressed file, which is compressed using
bzip2 algorithm and has *.smw* extension name (smw, abbreviation of sokoban's
middle ware);
* middle ware should defined its version, author, catalog and form
   * version format should fit PEP 386,
   * author declaration: \__author__ = 'your name'
   * catalog: `[catalog_name,...]`. Valid catalog_name includes read, write.
   read means write data to essence core, write means write data to remote.
   * form: extra info you want to get from a project. Syntax like:

   .. code-block:: python

      form = {
          "username": {
              "verbose": "Confluence Username"
          },
          "password": {
              "verbose": "Confluence Password",
              "type": "password"
          },
          "context_url": {
              "type": "url",
              "verbose": "Url of confluence context",
              "helper_text": "ep: https://developer.atlassian.com/"
          },
          "space": {
              "verbose": "Target Space"
          }
      }

   Field is an required text field by default, label of which is *verbose*.

* middleware can have following hook

   .. code-block:: python

       def on_install(db):
           """will be execute when installed.

           raise any exception to revert the installation.
           :param db: a database connection used for creating its tables if needed
           """
           pass

       def on_upgrade(db, pre):
           """will be execute when upgrade.

           raise any exception to revert the upgrade.
           :param db:
           :param pre: previous version code
           :return:
           """
           pass

       def on_uninstall(db):
           """will be execute when uninstalled.

           no matter what happened, the plugin will be removed eventually.
           """
           pass

       def on_bind(db, option, user_id, project_id, **kwargs):
           """will be called when an option is mounted.

           should return handled option to be saved.
           """
           pass

       def on_project_delete(db, project_id):
           """will be called when a project is deleted.
           """
           pass

difference
``````````

+ checkout client and push client should define a class named NetClient, read
filter and write markup should define a class named Filter
+ filters can define callbacks like on_install, on_uninstall, on_upgrade to
receive specific signals. Their signature will be discussed later.

Function signature and Class interface
--------------------------------------

.. code-block:: python

    class NetClient(object):
        """checkout client
        """
        def __init__(self, project_id, db, logger, form, **kwargs):
            """
            :param form: form object that contains information you specify
            before in form definition.
            """
            pass

        def open_project(self, project_path):
            """You should make sure the project exists in project_path.
            :param project_path: where the project root should be.
            """
            pass

        def update_project(self):
            """update the project.
            """
            pass

        def get_version(self):
            """get current version of the project
            """
            pass

        def get_lazy_change_log(self, end_pos=None,
                            begin_pos=None, max_count=None):
            """get an iterator for change log.
            :param end_pos: when None, it should current version of the project
            :param begin_pos: when None, it should be the initial version
            :param max_count: when not specify, should return all the logs
            in (begin_pos, end_pos]. If begin_pos is None, then return all logs
            happened before end_pos(included).
            :return: change logs. format should see following section.
            """
            pass

        def get_change_log(self, end_pos=None, begin_pos=None,
                       max_count=None, reverse=None):
            """get change logs
            :param reverse: sort the logs from newest to oldest.
            """
            pass

        def get_file(self, source_path, version=None):
            """return content of a file or list of files in a directory
             referenced by source_path.

            :param version: specific version of file
            :param source_path: relative path
            :return:
            """
            pass

        def copy_file(self, source_path, target_base_path,
                  version=None, cleanup=True):
            """copy a file or directory to target base path.

            for example, copy doc/readme.md to /tmp will result in
             /tmp/doc/readme.md
            :param source_path: if None, will checkout all files
            :param target_base_path: if specify, will copy the file to that
             directory rather than return as string. You may use absolute path.
            :param version:
            :param cleanup: whether cleanup all the untracked file under
             target_base_path
            :return:
            """
            pass

    class Filter(object):
        """read filter
        """
        def __init__(self, project_id, db, logger,
                    read_client=None, form=None, **kwargs):
            """
            :param project_name:
            :param db: a database connection.
            You should be aware that db produce a cursor type that return
             result as dict.
            :param logger: you should write log through logger.
            :param read_client: if you in read catalog, will give you a read
             client instance
            :param form:
            :return:
            """
            pass

        def merge_step(self, core_docs_tree, working_directory=None,
                   last_version=None, virtual_build=None,
                   skip_history=True):
            """merge the remote differences into essence version control step
            by step

            :param core_docs_tree: working root for docs. All changes should
             be cleaned up and update to that directory.
            :param working_directory: if you want to create directory or file,
            please put it under this directory.
            :param last_version: just merge changes since when. if not specify,
             will merge all changes.
            :param virtual_build: function that will build docs in virtual
             environment.
            :param skip_history: whether sync the historical version of docs
            :return: yield the logs that this step create
            """
            pass

        def merge(self, *args, **kwargs):
            """return logs in list, same signature as merge_step
            """
            pass


    class Filter(object):
        """write markup
        """
        def __init__(self, project_name, db, logger, write_client=None, form=None):
            """
            :param project_name:
            :param db: a database connection. You should be aware that db
             produce a cursor type that return result as dict.
            :param write_client:
            :param form:
            :return:
            """
            pass

        def apply(self, base_dir, outline, changes):
            """push logs to remote

            :param base_dir: all reference should not beyond this base_dir
            :param outline: outline of menu, see *core storage*
            :param changes: follow the format [{
                'operation': operation,  # 'add', 'modified', 'delete' or 'move'
                'content_type': content_type,  # 'page' or 'attachment'
                'path': path,  # path to documentation
                'second_path': second_path,  #  if operation is 'move', this field
                means target_path, else this field is optional.
            }, ...]
            """
            pass

    class NetClient(object):
        """push client
        """
        def __init__(self, project_id, db, logger, form, **kwargs):
            pass

        def register_attachment(self, attach, owner_page_id,
                            filename, content_type=None):
            """register attachment to page as filename.
            """
            pass

        def move_attachment(self, spid, sn, tpid, tn):
            """move attachment named sn from source page to target page and
             changes to be named tn
            """
            pass

        def delete_attachment(self, pid, name):
            pass

        def register_page(self, title, content, parent_id=None,
                mark_home=False):
            """add a page
            """
            pass

        def get_page(self, pid=None, title=None):
            """get the infomation of a page
            """
            pass

        def modified_page(self, pid, title, content, version=None,
                    parent_id=None, mark_home=False):
            """
            """
            pass

        def move_page(self, spid, tpid, position):
            """move a page to target position anchored by tpid.
            """
            pass

        def delete_page(self, pid):
            pass

        def close(self):
            pass

Data Format
-----------

There are some requirements for the data format that pass from filter to
netclient, or return by filter.

Change Log
``````````

There are two types of change logs. First is the log that pass from
 checkout client to read filter. Those logs should be json objects formatted as:

.. code-block:: json

   {
       "version": "change version id",
       "changed_files": [["action, could be move, modified, delete, add", "first_path", "second_path, valid only when action is move, means target path"], ...],
       "author": "author name",
       "email": "author email",
       "date": "the date change was commit",
       "commit_message": "commit message"
   }

Second is the logs that pass to write filter, it should be json array formatted as

.. code-block::  json

   [{
       "operation": "add, modified, delete or move",
       "content_type": "page or attachment",
       "path": "physical relative path to the documentation"
       "second_path": "valid only when operation is move, means target path",
   }, ...]

Core Documentation Storage
``````````````````````````

A documentation is a html file which should only contains specify attributes. All the restriction will be described below.

All tags in documentation should be list as following way.

If tag a follows tag b, then tag b should occupied one line. Otherwise leave as it is.

.. code-block:: html

   <b>
   <a>...</a>
   </b>
   <b>
   <a>This is multi
   line content</a>
   </b>
   <b>
   <a>This is a line with tag <c>...</c>
   </a>

There should never be any blank lines between two adjacent tags.

There should be a __meta__.json file in documentation root that indicates ownerships of docs, for example:

.. code-block:: json

   [{
       "path to file named 'Welcome to use XXX'": [{
           "path to file named 'Overview'": null
       }, {
           "path to file named 'Installation'": [{
               "path to file named 'Windows'": null
           }, {
               " path to file named 'Linux'": null
           }]
       }]
   }]

In anchor element, if url in href attribute contains two slash(`//`), then it will be treated as external link. Otherwise,
it should references an existing resources in the repository.

All allowed tags and attributes are listed as follow:

* html
* head
* meta
    * name
    * value
* title
* body
* div
    * id
* p
    * id
    * style
* h1
    * id
* h2
    * id
* h3
    * id
* h4
    * id
* h5
    * id
* h6
    * id
* span
    * id
    * style
    * data-type
* a
    * id
    * style
    * href
    * target
* img
    * id
    * width
    * height
    * src
    * alt
* table
    * id
* tbody
* th
* tr
* td
    * rowspan
    * colspan
* blockquote
* pre
    * data-lang
* code
* sub
* sup
* ul
* li
* ol
* em
* strong
* u
* small
* big
* dt
* dl
* dd

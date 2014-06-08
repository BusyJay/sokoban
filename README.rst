Sokoban
=======

Sokoban is project that aims to ease the pain of programmer who are busy in
 synchronizing documentation of their projects to other hosts.

Though sokoban is designed for a team with multiple projects, you can use it
 just for one project.

Installation
------------

1. install sokoban's dependencies first.

    Make sure you have docker, mysql, git installed and configured properly.

2. install the package.

        $ python setup.py install

3. configure the project to meet your own need.

4. some job is not run by the installation process but needed to be run.

        $ sokoban_postinstall.sh

Usage
-----

Sokoban is based on django, so all deploy methods that django supports should works fine.
However, sokoban is shipped with a sample uwsgi configuration file, so you can just start uwsgi by:

        # uwsgi --ini /etc/sokoban/uwsgi.ini

    Please make sure you have installed uwsgi.

Dependency
----------

- django >= 1.5 < 1.6 (tested with 1.5.5)
- MySQLdb-python (tested with 1.2.5)
- kerberos (tested with 1.1.1 [optional for kerberos login support])
- uwsgi (tested with 2.0.3 [optional for uwsgi support])

License
-------

MIT

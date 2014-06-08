.. _installation:

Installation
============

Sokoban use `docker` to provide sandbox, `git` to maintain core repo history. So you should install them first.

Also sokoban is writted in `python`, and compatible with Python 2.x.

Sokoban is not published to pypi yet. But you can install it from source.

1. You can get the source from github.

.. code-block:: bash

      $ git clone https://github.com/busyjay/sokoban.git

2. Then the packages by using the command.

   .. code-block:: bash

      # pip install .

   Or, just use python.

   .. code-block:: bash

      # python setup.py install

   In the later cases you should install the python packages requirements by your self. All requirements is listed in `requirements.txt` in the root directory of project.

3. You also need to run some post installation task.

   .. code-block:: bash

      # sokoban_postinstall.sh

You can also make a rpm package from source. More information refers to `Fedora Docs`_.

.. _Fedora Docs:https://fedoraproject.org/wiki/How_to_create_an_RPM_package

Optional dependence
-------------------

* kerberos (for kerberos login support)
* uwsgi (for uwsgi support)


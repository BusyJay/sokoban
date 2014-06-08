.. _quickstart:

QuickStart
==========

Start Server
------------

Sokoban is based on django, so all deploy methods that django supports should works fine.
However, sokoban is shipped with a sample uwsgi configuration file, so you can just start uwsgi by:

.. code-block:: bash

   # uwsgi --ini /etc/sokoban/uwsgi.ini

Please make sure you have installed uwsgi.

Initial Server
--------------

At first sokoban is started with no middleware installed. To findout what middleware is, you can read :ref:`middleware`.

To make sokoban actually work, you should install at lease for different type of middleware.


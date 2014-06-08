#!/usr/bin/env python2
import os
import sys

if __name__ == "__main__":
    # fixme delete following two line when release
    if os.path.abspath(os.path.curdir) not in sys.path:
        sys.path.append(os.path.abspath(os.path.curdir))
    try:
        sys.argv.remove('--debug')
        os.environ["SOKOBAN_DEBUG"] = 'True'
    except ValueError:
        pass
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sokoban.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

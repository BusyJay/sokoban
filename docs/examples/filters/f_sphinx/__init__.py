"""A filter that can parse sphinx docs
"""

__author__ = 'jay'
__version__ = (0, 0, 1, 'alpha', 0)

catalog = ['read']
form = {
    "lang" : {
        "verbose": "Language",
        "require": False,
        "type": "select",
        "choices": [["python2", "Python 2"], ["python3", "Python 3"]],
        "value": "python2",
    },
    "trigger_pattern": {
        "verbose": "Trigger Pattern",
        "require": False,
        "helper_text": "Sphinx will regenerate docs once trigger is matched."
                       " Empty means regenerate docs every commit.",
    },
    "docs_root": {
        "verbose": "Documentation Root",
        "helper_text": "Where the generated docs locate."
    },
    "working_dir": {
        "verbose": "Working Directory",
        "require": False,
        "helper_text": "Path to working tree that build command run in.",
    },
    "build_command": {
        "verbose": "Build Command",
        "require": False,
        "type": "textarea",
        "helper_text": "Command that builds docs. Empty means docs are"
                       " already there",
    },
    "ignore_errors": {
        "verbose": "Ignore Errors",
        "type": "checkbox",
        "value": False,
    },
}


def on_install(db):
    pass


def on_upgrade(db, pre):
    pass


def on_uninstall(db):
    pass

from main import Filter

__all__ = ['Filter']

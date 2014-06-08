"""A client interact with confluence, provide push method.
"""
__author__ = 'jay'
__version__ = (0, 0, 0, 'alpha', 0)

catalog = ['write']
form = {
    "username": {
        "require": True,
        "verbose": "Confluence Username"
    },
    "password": {
        "verbose": "Confluence Password",
        "require": True,
        "type": "password"
    },
    "context_url": {
        "type": "url",
        "require": True,
        "verbose": "Url of confluence context",
        "helper_text": "ep: https://developer.atlassian.com/"
    },
    "space": {
        "require": True,
        "verbose": "Target Space"
    },
    "parent_page_title": {
        "verbose": "Parent Page Title",
        "require": False,
        "helper_text": "all docs will be put under this page, leave empty "
                       "to put to the root."
    }
}
from main import NetClient

__all__ = ['NetClient']

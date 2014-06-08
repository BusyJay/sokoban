"""A client interact with git repository, provide pull and push method.
"""
__author__ = 'jay'
__version__ = (0, 0, 1, 'alpha', 0)

catalog = ['read']
form = {
    "url": {
        "type": "url",
        "require": True,
        "verbose": "Repository Url"
    },
    "branch_name": {
        'require': True,
        'value': 'master',
        'verbose': 'Track Branch',
        'helper_text': 'It will be the branch that track for documentation changes.'
    }
}
from main import NetClient
__all__ = ['NetClient']
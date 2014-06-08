from django.db import models
from django.utils.six import with_metaclass
import json

__author__ = 'jay'


class JsonField(with_metaclass(models.SubfieldBase, models.CharField)):
    """You should never save string in this field.

    """

    def to_python(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            try:
                return json.loads(value)
            except Exception:
                pass
        return value

    def get_prep_value(self, value):
        return json.dumps(value)


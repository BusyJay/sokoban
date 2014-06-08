import pickle
from django.db import models
from six import with_metaclass

__author__ = 'jay'


class PickleField(with_metaclass(models.SubfieldBase, models.Field)):
    def db_type(self, connection):
        return 'blob'

    def to_python(self, value):
        if isinstance(value, str):
            try:
                return pickle.loads(value)
            except Exception:
                pass
        return value

    def get_prep_value(self, value):
        return pickle.dumps(value)

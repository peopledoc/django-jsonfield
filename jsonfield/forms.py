import json

from django.forms import CharField, ValidationError
from django.utils.encoding import force_text

from jsonfield.utils import string_types
from jsonfield.widgets import JSONWidget


class JSONFormField(CharField):
    empty_values = (None, '')

    def __init__(self, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = JSONWidget
        super(JSONFormField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, string_types) and value:
            try:
                return json.loads(value)
            except ValueError as exc:
                raise ValidationError(
                    'JSON decode error: %s' % (force_text(exc.args[0]),)
                )
        else:
            return value

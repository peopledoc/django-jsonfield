import json

from django.forms import Textarea

from jsonfield.encoder import JSONEncoder
from jsonfield.utils import string_types


class JSONWidget(Textarea):
    def format_value(self, value):
        if value is None:
            return ''

        if not isinstance(value, string_types):
            return json.dumps(value, ensure_ascii=False, indent=2,
                              cls=JSONEncoder)

        return value

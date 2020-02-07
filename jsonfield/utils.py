import datetime
import six

from decimal import Decimal


def json_default(o):
    if hasattr(o, 'to_json'):
        return o.to_json()
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, datetime.datetime):
        if o.tzinfo:
            return o.strftime('%Y-%m-%dT%H:%M:%S%z')
        return o.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(o, datetime.date):
        return o.strftime("%Y-%m-%d")
    if isinstance(o, datetime.time):
        if o.tzinfo:
            return o.strftime('%H:%M:%S%z')
        return o.strftime("%H:%M:%S")
    if isinstance(o, set):
        return list(o)

    raise TypeError(repr(o) + " is not JSON serializable")


def _resolve_object_path(dotted_name):
    if isinstance(dotted_name, six.string_types):
        path = dotted_name.split('.')
        module = __import__(dotted_name.rsplit('.', 1)[0])
        for item in path[1:-1]:
            module = getattr(module, item)
        return getattr(module, path[-1])

    return dotted_name

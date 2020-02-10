from importlib import import_module

try:
    from django.utils.six import string_types, PY3
except ImportError:
    from six import string_types, PY3  # noqa


def resolve_object_from_path(class_path):
    if isinstance(class_path, string_types):
        try:
            module_name, class_name = class_path.rsplit('.', 1)
            module = import_module(module_name)
            return getattr(module, class_name)
        except ImportError:
            raise
        except Exception:
            raise ImportError("Unable to import '{}'".format(class_path))

    return class_path

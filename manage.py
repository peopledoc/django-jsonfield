#!/usr/bin/env python
import os
import sys
import warnings

if __name__ == "__main__":
    """
    Standalone django model test with a 'memory-only-django-installation'.
    You can play with a django model without a complete django app installation.
    http://www.djangosnippets.org/snippets/1044/
    """
    warnings.filterwarnings("always", category=DeprecationWarning)
    warnings.filterwarnings("once", category=PendingDeprecationWarning)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # Project is named microweb and contains a module called microweb (created by django).
    # This is not on sys.path when runserver is started, so add microweb.microweb to path.
    project_package = os.path.join(os.path.dirname(os.path.abspath(__file__)), "microweb")
    sys.path.insert(0, project_package)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "microweb.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

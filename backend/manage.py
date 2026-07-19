#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _reexec_with_project_venv():
    """Use the project virtualenv when manage.py is started with global Python."""
    if os.environ.get('NOTCHIRE_SKIP_VENV_REEXEC') == '1':
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(base_dir, 'venv', 'bin', 'python')
    if not os.path.exists(venv_python):
        return

    if sys.prefix != getattr(sys, 'base_prefix', sys.prefix):
        return

    os.environ['NOTCHIRE_SKIP_VENV_REEXEC'] = '1'
    os.execv(venv_python, [venv_python, *sys.argv])


def main():
    """Run administrative tasks."""
    _reexec_with_project_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notchfire_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

"""Production WSGI entrypoint for Stillbrook.

The repository contains both a top-level ``app.py`` (the fully configured
Flask application, including the WAF and challenge routes) and an ``app/``
Python package. Python resolves ``import app`` to the package, so the WSGI
callable cannot be referenced as ``app:app``. This module loads the root
``app.py`` by file path under a distinct module name and exposes its
``app`` object for gunicorn.
"""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
_APP_FILE = os.path.join(_ROOT, "app.py")

_spec = importlib.util.spec_from_file_location("stillbrook_root_app", _APP_FILE)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

#: The WSGI application object gunicorn serves.
app = _module.app

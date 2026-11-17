"""
Loads modules from the project's top-level logging/detections/ folder
WITHOUT ever writing `import logging.detections.xxx` anywhere in
application code.

Why this exists: the project's top-level folder is named `logging/`,
which collides with Python's stdlib `logging` module. A plain
`from logging.detections.idor import check_idor` works by accident in
a standalone test (see tests/test_detections.py's comment on this), but
inside application code that runs on every request, it would shadow the
stdlib `logging` module for the ENTIRE PROCESS the first time it's
imported -- silently breaking Flask/Werkzeug's own internal logging,
with no error raised at import time to warn you.

Every detection module gets loaded through here, by file path via
importlib, instead. Add one line per new detection as sprints add them.
"""
import importlib.util
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DETECTIONS_DIR = os.path.join(_PROJECT_ROOT, "logging", "detections")


def _load(module_name: str, filename: str):
    path = os.path.join(_DETECTIONS_DIR, filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# One entry per detection module. Application code imports from HERE,
# never directly from the logging/ package path.
idor_detection = _load("stillbrook_idor_detection", "idor.py")
brute_force_detection = _load("stillbrook_brute_force_detection", "brute_force.py")

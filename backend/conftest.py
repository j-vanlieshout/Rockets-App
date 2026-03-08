# conftest.py
# Ensures the backend/ directory is on sys.path so all imports work correctly
# when running pytest from the backend/ folder.

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
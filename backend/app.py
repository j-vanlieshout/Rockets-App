# app.py
# Entry point for uvicorn — run from the backend/ folder:
#   python -m uvicorn app:app --reload

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from api.main import app
# wsgi.py
import os, sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tickets_app import app  # importa la instancia Flask llamada "app"

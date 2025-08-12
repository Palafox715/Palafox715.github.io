# wsgi.py
from tickets_app import app  # importa la instancia creada en tickets_app.py

# (opcional) healthcheck directo
@app.route("/__health")
def __health():
    return "OK"

import sys
import os

# Agregamos la carpeta 'App' al camino de búsqueda de Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'App')))

# Importamos 'app' desde el archivo 'app.py' que está dentro de la carpeta 'App'
try:
    from app import app as application
except ImportError:
    # Por si el archivo interno también tiene mayúscula: App.py
    from App import app as application

if __name__ == "__main__":
    application.run()
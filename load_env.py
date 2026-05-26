import os
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Charger les variables d'environnement depuis .env
if load_dotenv:
    load_dotenv()

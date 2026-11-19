"""Solo laboratorio local. Nunca apunta a SQLite o MEDIA_ROOT operativos."""
from config.settings import *

LAB_ROOT = (BASE_DIR / "output/experimental_pilotos").resolve()
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": LAB_ROOT / "laboratorio.sqlite3"}}
MEDIA_ROOT = LAB_ROOT / "media"
ROOT_URLCONF = "experimentos.pilotos.urls"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
STORAGES = {
    "default": {"BACKEND": "experimentos.pilotos.storage.FuentesStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
SESSION_COOKIE_NAME = "epp_lab_session"
CSRF_COOKIE_NAME = "epp_lab_csrf"
LOGIN_URL = "/admin/login/"
DEBUG = False  # No mostrar trazas ni rutas locales en errores HTTP del laboratorio.
# Plantillas propias del portal: los módulos operativos no se modifican.
TEMPLATES = [{**t, "DIRS": [BASE_DIR / "experimentos/pilotos/templates", *t["DIRS"]]} for t in TEMPLATES]
MIDDLEWARE = [*MIDDLEWARE, "experimentos.pilotos.navegacion.NavegacionLaboratorio"]
STATICFILES_DIRS = [BASE_DIR / "static"]

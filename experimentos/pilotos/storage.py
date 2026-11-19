from django.core.files.storage import FileSystemStorage
from django.core.exceptions import SuspiciousFileOperation
from .fuentes import FUENTES


class FuentesStorage(FileSystemStorage):
    """Los alias fuente se leen del original; todos los resultados van al laboratorio."""
    def path(self, name):
        if name in FUENTES:
            return str(FUENTES[name])
        return super().path(name)

    def save(self, name, content, max_length=None):
        if name in FUENTES or name.startswith("fuentes/"):
            raise SuspiciousFileOperation("Los videos fuente son de solo lectura.")
        return super().save(name, content, max_length=max_length)

    def delete(self, name):
        if name in FUENTES or name.startswith("fuentes/"):
            raise SuspiciousFileOperation("No se eliminan fuentes desde el laboratorio.")
        return super().delete(name)

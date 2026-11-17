"""Corta cargas excesivas antes de escribir el archivo completo en disco."""
from django.core.files.uploadhandler import FileUploadHandler, StopUpload

from .videos import MAX_BYTES


class LimiteVideoUploadHandler(FileUploadHandler):
    def __init__(self, request=None):
        super().__init__(request)
        self.total = 0
        self.aplica = request is not None and (
            request.path.startswith("/produccion/")
            or request.path.startswith("/admin/produccion/analisisproduccion/")
        )

    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        if self.aplica and self.total > MAX_BYTES:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None

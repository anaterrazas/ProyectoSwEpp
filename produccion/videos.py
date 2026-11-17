"""Validación de MP4 sin confiar en extensión ni Content-Type del cliente."""
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import imageio_ffmpeg
from django.core.exceptions import ValidationError

MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS = 120
MAX_PIXELS = 1920 * 1080
MAX_FPS = 60
PROBE_TIMEOUT = 10
DECODE_TIMEOUT = 30


def _ejecutar(argumentos, timeout):
    return subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-hide_banner",
         "-max_alloc", "67108864", *argumentos],
        capture_output=True, text=True, errors="replace", timeout=timeout,
    )


def validar_video(archivo):
    """Copia acotada y decodificación aislada; restaura el cursor del archivo."""
    posicion = archivo.tell()
    try:
        if Path(archivo.name).suffix.lower() != ".mp4" or not 0 < archivo.size <= MAX_BYTES:
            raise ValidationError("Use un MP4 de hasta 100 MiB.")
        archivo.seek(0)
        cabecera = archivo.read(12)
        if len(cabecera) != 12 or cabecera[4:8] != b"ftyp" or cabecera[8:12] not in (
            b"isom", b"iso2", b"iso5", b"iso6", b"mp41", b"mp42", b"avc1",
        ):
            raise ValidationError("El contenido no es un MP4 admitido.")
        archivo.seek(0)
        with TemporaryDirectory(prefix="epp_video_") as temporal:
            ruta = Path(temporal) / "entrada.mp4"
            total = 0
            with ruta.open("wb") as destino:
                while bloque := archivo.read(1024 * 1024):
                    total += len(bloque)
                    if total > MAX_BYTES:
                        raise ValidationError("El video supera 100 MiB.")
                    destino.write(bloque)
            entrada = ["-protocol_whitelist", "file,pipe", "-threads", "1", "-i", str(ruta)]
            info = _ejecutar(entrada, PROBE_TIMEOUT).stderr
            duracion = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", info)
            video = re.search(r"Video: (h264|mpeg4)\b[^\n]*?\b(\d{2,5})x(\d{2,5})\b[^\n]*?([\d.]+) fps", info)
            if not duracion or not video:
                raise ValidationError("MP4 inválido: se requiere video H.264 o MPEG-4 con duración y FPS conocidos.")
            horas, minutos, segundos = map(float, duracion.groups())
            segundos += horas * 3600 + minutos * 60
            _, ancho, alto, fps = video.groups()
            if not (0 < segundos <= MAX_SECONDS and 0 < float(fps) <= MAX_FPS
                    and int(ancho) <= 1920 and int(alto) <= 1920
                    and int(ancho) * int(alto) <= MAX_PIXELS):
                raise ValidationError("Límites: 120 segundos, Full HD y 60 FPS.")
            # No red, un hilo, límite temporal y decodificación real antes de aceptar.
            resultado = _ejecutar([
                "-v", "error", "-xerror", *entrada, "-map", "0:v:0", "-an", "-sn", "-dn",
                "-t", str(MAX_SECONDS + 1), "-threads", "1", "-progress", "pipe:1",
                "-nostats", "-f", "null", "-",
            ], DECODE_TIMEOUT)
            tiempos = re.findall(r"out_time_us=(\d+)", resultado.stdout)
            frames = re.findall(r"frame=(\d+)", resultado.stdout)
            if (resultado.returncode or not tiempos or not frames or int(frames[-1]) <= 0
                    or int(tiempos[-1]) > MAX_SECONDS * 1_000_000
                    or int(frames[-1]) > MAX_SECONDS * MAX_FPS):
                raise ValidationError("Video dañado o fuera de los límites de procesamiento.")
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationError("No se pudo validar el video dentro del tiempo permitido.") from error
    finally:
        archivo.seek(posicion)


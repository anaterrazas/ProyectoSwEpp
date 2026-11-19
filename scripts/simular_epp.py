"""Prueba real del flujo EPP con video y base aislada en memoria.

Lee la configuración existente en SQLite en modo lectura. Solo escribe resultados
nuevos en media/resultados_ia; las detecciones y el usuario de prueba son efímeros.
Ejecutar desde la raíz: python -B scripts/simular_epp.py --camara 1
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camara", type=int, default=1)
    args = parser.parse_args()
    with sqlite3.connect(f"file:{(ROOT / 'db.sqlite3').as_posix()}?mode=ro", uri=True) as db:
        camara = db.execute(
            "SELECT c.id,c.nombre,c.area_id,c.archivo_video,a.nombre,c.tipo_monitoreo,c.tipo_fuente "
            "FROM administracion_camara c JOIN administracion_areatrabajo a ON a.id=c.area_id WHERE c.id=?",
            (args.camara,),
        ).fetchone()
        if not camara or camara[5:] != ("EPP", "VIDEO"):
            raise ValueError("Seleccione una cámara EPP con archivo de video.")
        equipos = db.execute(
            "SELECT e.nombre FROM administracion_equipoproteccion e "
            "JOIN administracion_areatrabajo_equipos_obligatorios r ON r.equipoproteccion_id=e.id "
            "WHERE r.areatrabajo_id=?", (camara[2],),
        ).fetchall()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    from django.conf import settings
    settings.DATABASES["default"]["NAME"] = ":memory:"
    settings.ALLOWED_HOSTS = ["testserver"]
    django.setup()
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.test import Client
    from django.urls import reverse
    from administracion.models import AreaTrabajo, Camara, EquipoProteccion
    from seguridad.piloto import equipos_piloto
    equipos_piloto([nombre for nombre, in equipos])
    video = (Path(settings.MEDIA_ROOT) / camara[3]).resolve()
    if not video.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not video.is_file():
        raise ValueError("Video ausente o fuera de media.")
    sha = hashlib.sha256(video.read_bytes()).hexdigest()
    call_command("migrate", verbosity=0, interactive=False)
    area = AreaTrabajo.objects.create(pk=camara[2], nombre=camara[4])
    for nombre, in equipos:
        area.equipos_obligatorios.add(EquipoProteccion.objects.create(nombre=nombre))
    Camara.objects.create(pk=camara[0], nombre=camara[1], area=area,
                          tipo_monitoreo="EPP", tipo_fuente="VIDEO", archivo_video=camara[3])
    usuario = get_user_model().objects.create_user(username="simulacion_efimera")
    usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="seguridad"))
    cliente = Client()
    cliente.force_login(usuario)
    cliente.post(reverse("analizar_camara", args=[camara[0]]))
    ejecucion = cliente.session.get(f"piloto_{camara[0]}")
    if not ejecucion:
        raise RuntimeError("La prueba no produjo un reporte; consulte el error del procesador.")
    if hashlib.sha256(video.read_bytes()).hexdigest() != sha:
        raise RuntimeError("El original cambió durante la simulación.")
    print(json.dumps({"modo": "PRUEBA_VIDEO", "base_datos": "memoria",
                      "reporte_url": reverse("reporte_piloto", args=[camara[0], ejecucion]),
                      "original_sin_cambios": True}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

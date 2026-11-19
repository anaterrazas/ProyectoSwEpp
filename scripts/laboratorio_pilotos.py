"""Inicializa y abre únicamente el laboratorio local, sin clonar SQLite operativo."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    os.environ["DJANGO_SETTINGS_MODULE"] = "experimentos.pilotos.settings"
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    if args.init:
        settings.LAB_ROOT.mkdir(parents=True, exist_ok=True)
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        call_command("migrate", verbosity=0, interactive=False)
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from administracion.models import AreaTrabajo, Camara, EquipoProteccion
        from experimentos.pilotos.fuentes import FUENTES
        area, _ = AreaTrabajo.objects.get_or_create(pk=1, defaults={"nombre": "Área de referencia · laboratorio"})
        for nombre in ("Casco", "Chaleco"):
            area.equipos_obligatorios.add(EquipoProteccion.objects.get_or_create(nombre=nombre)[0])
        for numero, alias in enumerate(list(FUENTES)[:2], 1):
            Camara.objects.get_or_create(pk=numero, defaults={"nombre": f"Video EPP {numero} · laboratorio",
                "area": area, "tipo_monitoreo": "EPP", "tipo_fuente": "VIDEO", "archivo_video": alias})
        usuario, creado = get_user_model().objects.get_or_create(username="piloto", defaults={"is_staff": True})
        if creado:
            clave = secrets.token_urlsafe(18)
            usuario.set_password(clave)
            usuario.save()
            (settings.LAB_ROOT / "acceso_local.json").write_text(json.dumps({
                "usuario": "piloto", "clave": clave, "url": "http://127.0.0.1:8010/monitoreo/",
                "alcance": "Solo laboratorio local, sin cuentas operativas"}, indent=2), encoding="utf-8")
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label__in=["seguridad", "administracion"]))
        usuario.user_permissions.add(*Permission.objects.filter(content_type__app_label="produccion", codename__in=["view_analisisproduccion", "change_inspeccioncalidad"]))
        # Copiar solo reportes anteriores y sus evidencias; no copiar fuentes ni anotaciones.
        fuentes = ROOT / "media/resultados_ia/camara_1"
        destino = Path(settings.MEDIA_ROOT) / "resultados_ia/camara_1"
        for reporte in fuentes.glob("*/reporte.json"):
            carpeta = destino / reporte.parent.name
            if not carpeta.exists():
                shutil.copytree(reporte.parent, carpeta)
        print("Laboratorio preparado. Acceso: output/experimental_pilotos/acceso_local.json")
    if args.serve:
        if not Path(settings.DATABASES["default"]["NAME"]).is_file():
            raise SystemExit("Ejecute primero --init")
        call_command("runserver", "127.0.0.1:8010", use_reloader=False)
    if not args.init and not args.serve:
        parser.print_help()


if __name__ == "__main__":
    main()

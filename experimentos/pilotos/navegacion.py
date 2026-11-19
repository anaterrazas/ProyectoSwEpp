"""Añade retorno al portal en pantallas heredadas, solo con settings de laboratorio."""
from django.urls import reverse
from .catalogo import permite


class NavegacionLaboratorio:
    def __init__(self, get_response):
        self.get_response=get_response

    def __call__(self, request):
        respuesta=self.get_response(request)
        if (request.user.is_authenticated and respuesta.status_code==200
                and (request.path.startswith("/monitoreo/") or request.path=="/calidad/")
                and not respuesta.streaming and "text/html" in respuesta.get("Content-Type", "")):
            enlaces=[(reverse("demo_inicio"),"← Plataforma de demostración")]
            for modulo,nombre in [("epp","Seguridad EPP"),("calidad","Control de Calidad")]:
                if permite(request.user,modulo):enlaces.append((reverse("demo_modulo",args=[modulo]),nombre))
            enlaces.append((reverse("demo_historial"),"Historial"))
            nav='<nav aria-label="Plataforma de demostración" style="display:flex;flex-wrap:wrap;gap:18px;background:#101f32;padding:16px 24px;font:14px Segoe UI,Arial,sans-serif">'+''.join(f'<a style="color:white;text-decoration:underline" href="{url}">{nombre}</a>' for url,nombre in enlaces)+'</nav>'
            import re
            texto=respuesta.content.decode(respuesta.charset)
            texto=re.sub(r"(<body\b[^>]*>)",lambda m:m.group(1)+nav,texto,count=1,flags=re.I)
            respuesta.content=texto.encode(respuesta.charset)
            if "Content-Length" in respuesta:respuesta["Content-Length"]=len(respuesta.content)
        return respuesta

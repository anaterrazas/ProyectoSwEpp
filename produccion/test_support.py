from django.contrib.auth.models import Permission


def autorizar_supervisor(usuario):
    usuario.user_permissions.add(*Permission.objects.filter(
        content_type__app_label="produccion",
        codename__in=["add_analisisproduccion", "change_analisisproduccion", "change_inspeccioncalidad"],
    ))
    return usuario

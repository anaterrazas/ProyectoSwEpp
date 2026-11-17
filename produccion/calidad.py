from django.db.models import Count, Q


def resumen_calidad(analisis):
    resumen = analisis.inspecciones.aggregate(
        conformes=Count("pk", filter=Q(resultado="CONFORME")),
        defectuosas=Count("pk", filter=Q(resultado="DEFECTUOSO")),
        pendientes=Count("pk", filter=Q(resultado="REVISION")),
        registradas=Count("pk"),
    )
    total = analisis.cantidad_contada
    resumen["total"] = total
    resumen["porcentaje_conformidad"] = 100 * resumen["conformes"] / total if total else 0
    resumen["porcentaje_defectos"] = 100 * resumen["defectuosas"] / total if total else 0
    return resumen


def actualizar_lote(lote):
    """Invocar dentro de una transacción con el lote bloqueado."""
    vigente = lote.analisis.filter(estado="COMPLETADO").order_by("-fecha_analisis", "-pk").first()
    if vigente is None:
        return
    resumen = resumen_calidad(vigente)
    lote.cantidad_producida = resumen["total"]
    lote.cantidad_conforme = resumen["conformes"]
    lote.cantidad_defectuosa = resumen["defectuosas"]
    completo = resumen["registradas"] == resumen["total"] and not resumen["pendientes"]
    lote.estado = "FINALIZADO" if completo else "EN_PROCESO"
    lote.save(update_fields=["cantidad_producida", "cantidad_conforme", "cantidad_defectuosa", "estado"])

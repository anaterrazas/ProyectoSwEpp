"""CU-11: consultas de solo lectura; no sincroniza ni modifica datos históricos."""
import csv

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import AnalisisProduccion, LoteProduccion, Producto


def filtro_tipo(request):
    tipo = request.GET.get("tipo", "")
    if tipo and tipo not in Producto.Tipo.values:
        raise ValueError("Tipo de producto inválido. Seleccione Botellas, Cajas o Bolsas.")
    return tipo


def analisis_con_resultados():
    return AnalisisProduccion.objects.annotate(
        conformes=Count("inspecciones", filter=Q(inspecciones__resultado="CONFORME")),
        defectuosas=Count("inspecciones", filter=Q(inspecciones__resultado="DEFECTUOSO")),
        pendientes=Count("inspecciones", filter=Q(inspecciones__resultado="REVISION")),
        registradas=Count("inspecciones"),
    ).order_by("-fecha_analisis", "-pk")


def metricas(total, conformes, defectuosas, pendientes, registradas):
    return dict(total=total, conformes=conformes, defectuosas=defectuosas,
                pendientes=pendientes, sin_registro=max(total - registradas, 0),
                porcentaje_conformidad=100 * conformes / total if total else 0,
                porcentaje_defectos=100 * defectuosas / total if total else 0)


def resumen_analisis(analisis):
    return metricas(analisis.cantidad_contada, analisis.conformes, analisis.defectuosas,
                    analisis.pendientes, analisis.registradas)


def lotes_con_vigente():
    ultimo = AnalisisProduccion.objects.filter(
        lote_id=OuterRef("pk"), estado="COMPLETADO"
    ).order_by("-fecha_analisis", "-pk")
    return LoteProduccion.objects.select_related("producto").annotate(
        vigente_id=Subquery(ultimo.values("pk")[:1]), numero_analisis=Count("analisis")
    ).order_by("-fecha_creacion", "-pk")


def filas_lotes(lotes):
    lotes = list(lotes)
    vigentes = {a.pk: a for a in analisis_con_resultados().filter(
        pk__in=[l.vigente_id for l in lotes if l.vigente_id]
    )}
    return [dict(lote=l, vigente=vigentes.get(l.vigente_id),
                 resumen=resumen_analisis(vigentes[l.vigente_id]) if l.vigente_id in vigentes else None)
            for l in lotes]


@login_required(login_url="/admin/login/")
@require_safe
def panel_resultados(request):
    try:
        tipo = filtro_tipo(request)
    except ValueError as error:
        return HttpResponseBadRequest(str(error))
    # Dos consultas para los lotes y sus mediciones, sin consultas por fila.
    lotes = lotes_con_vigente()
    if tipo:
        lotes = lotes.filter(producto__tipo=tipo)
    filas = filas_lotes(lotes)
    valores = [f["resumen"] for f in filas if f["resumen"] is not None]
    totales = {k: sum(r[k] for r in valores) for k in
               ("total", "conformes", "defectuosas", "pendientes", "sin_registro")}
    resumen = metricas(totales["total"], totales["conformes"], totales["defectuosas"],
                       totales["pendientes"], totales["total"] - totales["sin_registro"])
    maximo = max((r["total"] for r in valores), default=0) or 1
    grafico = [dict(codigo=f["lote"].codigo, total=f["resumen"]["total"],
                    ancho=100 * f["resumen"]["total"] / maximo)
               for f in filas if f["resumen"] is not None][:12]
    return render(request, "produccion/panel_resultados.html", {
        "resumen": resumen, "total_lotes": len(filas), "con_resultados": len(valores),
        "pagina": Paginator(filas, 20).get_page(request.GET.get("page")),
        "grafico": grafico, "grafico_calidad": _grafico_calidad(resumen),
        "tipo_seleccionado": tipo, "tipos_producto": Producto.Tipo.choices,
    })


def _grafico_calidad(resumen):
    return [dict(nombre=nombre, cantidad=resumen[campo], color=color,
                 ancho=100 * resumen[campo] / resumen["total"] if resumen["total"] else 0)
            for campo, nombre, color in (
                ("conformes", "Conformes", "verde"), ("defectuosas", "Defectuosas", "rojo"),
                ("pendientes", "Pendientes de revisión", "ambar"),
                ("sin_registro", "Sin registro de inspección", "gris"))]


@login_required(login_url="/admin/login/")
@require_safe
def detalle_lote(request, lote_id):
    lote = get_object_or_404(lotes_con_vigente(), pk=lote_id)
    analisis = list(analisis_con_resultados().filter(lote=lote))
    for a in analisis:
        a.resumen_consulta = resumen_analisis(a)
    vigente = next((a for a in analisis if a.pk == lote.vigente_id), None)
    return render(request, "produccion/detalle_lote.html", {
        "lote": lote, "analisis": analisis, "vigente": vigente,
        "resumen": vigente.resumen_consulta if vigente else None,
    })


def _celda(valor):
    # Evitar ejecutar fórmulas al abrir datos de usuario en una hoja de cálculo.
    texto = str(valor) if valor is not None else ""
    return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n")) else texto


@login_required(login_url="/admin/login/")
@require_safe
def descargar_resultados(request, lote_id=None):
    try:
        tipo = filtro_tipo(request)
    except ValueError as error:
        return HttpResponseBadRequest(str(error))
    lotes = lotes_con_vigente()
    if tipo:
        lotes = lotes.filter(producto__tipo=tipo)
    if lote_id is not None:
        get_object_or_404(lotes, pk=lote_id)
        lotes = lotes.filter(pk=lote_id)
    filas = filas_lotes(lotes)
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="resultados_produccion%s.csv"' % (
        f"_lote_{lote_id}" if lote_id is not None else "")
    respuesta.write("\ufeff")
    escritor = csv.writer(respuesta, delimiter=";")
    escritor.writerow(["Tipo", "Lote", "Producto", "Analisis", "Vigente", "Estado", "Fecha",
                        "Producidas", "Conformes", "Defectuosas", "Pendientes", "Sin registro",
                        "Conformidad %", "Defectos %", "Unidad", "Resultado", "Criterio", "Tipo defecto", "Observaciones", "Tipo producto", "Origen unidades"])
    def escribir(fila, tipo_producto, origen):
        fila = fila + [""] * (19 - len(fila))
        fila.extend([tipo_producto, origen])
        escritor.writerow([_celda(v) for v in fila])
    for f in filas:
        lote, a, r = f["lote"], f["vigente"], f["resumen"]
        escribir(["LOTE_ACTUAL", lote.codigo, lote.producto.nombre, a.pk if a else "", "Si" if a else "No",
                  lote.get_estado_display(), lote.fecha_creacion.isoformat()] +
                 ([r[k] for k in ("total", "conformes", "defectuosas", "pendientes", "sin_registro",
                                  "porcentaje_conformidad", "porcentaje_defectos")] if r else [""] * 7),
                 lote.producto.get_tipo_display(), a.get_origen_display() if a else "")
    por_id = {f["lote"].pk: f["lote"] for f in filas}
    historial = analisis_con_resultados().filter(lote_id__in=por_id).prefetch_related("inspecciones__criterio")
    for a in historial:
        lote = por_id[a.lote_id]
        r = resumen_analisis(a)
        base = [lote.codigo, lote.producto.nombre, a.pk, "Si" if a.pk == lote.vigente_id else "No", a.get_estado_display(), a.fecha_analisis.isoformat()]
        escribir(["ANALISIS"] + base + [r[k] for k in ("total", "conformes", "defectuosas", "pendientes", "sin_registro", "porcentaje_conformidad", "porcentaje_defectos")], lote.producto.get_tipo_display(), a.get_origen_display() if a else "")
        for i in a.inspecciones.all():
            escribir(["INSPECCION"] + base + [""] * 7 + [i.identificador, i.get_resultado_display(),
                     i.criterio.nombre if i.criterio else "", i.tipo_defecto, i.observacion], lote.producto.get_tipo_display(), a.get_origen_display() if a else "")
    return respuesta

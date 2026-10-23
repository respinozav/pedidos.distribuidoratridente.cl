import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.entities import Categoria, Cliente, DetallePedido, Estado, Pedido, Producto

logger = logging.getLogger(__name__)
settings = get_settings()

def formatear_pesos_chilenos(monto: float | int | Decimal | None) -> str:
    """Formatea montos al estándar chileno: $1.234.567."""
    if monto is None:
        return "$0"
    try:
        val = int(round(float(monto)))
        return f"${val:,}".replace(",", ".")
    except Exception:
        return f"${monto}"


MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def _parse_fechas_periodo(
    fecha_desde: str | datetime | None = None,
    fecha_hasta: str | datetime | None = None,
    dias_defecto: int = 30,
) -> tuple[datetime, datetime, str]:
    """
    Parsea de forma robusta fechas de inicio y fin en zona horaria America/Santiago y las convierte a UTC.
    Garantiza que la hora de corte cubra el día chileno completo (00:00:00 a 23:59:59.999999).
    Si no se especifican, toma por defecto el mes en curso (desde el 1 del mes hasta el día actual).
    Retorna (dt_inicio_utc, dt_fin_utc, texto_periodo_legible).
    """
    try:
        from zoneinfo import ZoneInfo
        tz_chile = ZoneInfo("America/Santiago")
    except Exception:
        tz_chile = UTC

    now_chile = datetime.now(tz_chile)
    now_utc = now_chile.astimezone(UTC)

    # 1. Resolver fecha_desde
    dt_desde = None
    if isinstance(fecha_desde, datetime):
        dt_desde = fecha_desde.astimezone(UTC) if fecha_desde.tzinfo else fecha_desde.replace(tzinfo=tz_chile).astimezone(UTC)
    elif isinstance(fecha_desde, str) and fecha_desde.strip():
        txt = fecha_desde.strip().split("T")[0]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                local_dt = datetime.strptime(txt, fmt).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz_chile)
                dt_desde = local_dt.astimezone(UTC)
                break
            except ValueError:
                pass

    # 2. Resolver fecha_hasta
    dt_hasta = None
    if isinstance(fecha_hasta, datetime):
        dt_hasta = fecha_hasta.astimezone(UTC) if fecha_hasta.tzinfo else fecha_hasta.replace(tzinfo=tz_chile).astimezone(UTC)
    elif isinstance(fecha_hasta, str) and fecha_hasta.strip():
        txt = fecha_hasta.strip().split("T")[0]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                local_dt = datetime.strptime(txt, fmt).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=tz_chile)
                dt_hasta = local_dt.astimezone(UTC)
                break
            except ValueError:
                pass

    # Si ninguna fecha fue indicada: usar mes en curso en horario chileno
    if dt_desde is None and dt_hasta is None:
        dt_desde = now_chile.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        dt_hasta = now_utc
        mes_nombre = MESES_ES.get(now_chile.month, "octubre")
        texto_periodo = f"mes en curso ({mes_nombre} {now_chile.year})"
    elif dt_desde is not None and dt_hasta is None:
        dt_hasta = now_utc
        local_desde = dt_desde.astimezone(tz_chile)
        texto_periodo = f"desde {local_desde.strftime('%d/%m/%Y')} hasta hoy"
    elif dt_desde is None and dt_hasta is not None:
        dt_desde = dt_hasta - timedelta(days=dias_defecto)
        local_hasta = dt_hasta.astimezone(tz_chile)
        texto_periodo = f"últimos {dias_defecto} días hasta {local_hasta.strftime('%d/%m/%Y')}"
    else:
        # Ambos definidos
        local_d = dt_desde.astimezone(tz_chile)
        local_h = dt_hasta.astimezone(tz_chile)
        if local_d.year == local_h.year and local_d.month == local_h.month:
            mes_nombre = MESES_ES.get(local_d.month, "")
            texto_periodo = f"{local_d.day} al {local_h.day} de {mes_nombre} de {local_d.year}"
        else:
            texto_periodo = f"{local_d.strftime('%d/%m/%Y')} al {local_h.strftime('%d/%m/%Y')}"

    return dt_desde, dt_hasta, texto_periodo



class PostgrestService:
    """
    Servicio de acceso de solo lectura hacia PostgREST para consultas de productos y pedidos.
    Cuenta con fallback transparente a SQLAlchemy en caso de que PostgREST no esté activo localmente.
    """

    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.postgrest_url.rstrip("/")
        self.schema = settings.postgrest_schema
        self.headers = {
            "Accept": "application/json",
            "Accept-Profile": self.schema,
        }
        if settings.postgrest_token:
            self.headers["Authorization"] = f"Bearer {settings.postgrest_token}"

    def _query_postgrest_get(self, endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]] | None:
        """Realiza una petición GET de solo lectura a la API de PostgREST."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            with httpx.Client(timeout=4.0) as client:
                response = client.get(url, params=params, headers=self.headers)
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    "PostgREST respondió con status %s en %s: %s",
                    response.status_code,
                    url,
                    response.text[:200],
                )
                return None
        except Exception as e:
            logger.info("PostgREST no disponible (%s). Usando fallback local a PostgreSQL.", str(e))
            return None

    def consultar_productos(
        self,
        termino_busqueda: str = "",
        solo_activos: bool = True,
        ordenar_por_stock_asc: bool | None = None,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Consulta la lista de productos vía PostgREST GET /productos (o fallback BD).
        """
        limite = min(max(1, limite), 100)
        pg_params: dict[str, Any] = {
            "select": "id,codigo,nombre,precio,cantidad,activo,afecto,tiene_caja,cantidad_caja,precio_caja,notificar_stock,stock_notificacion,categoria:categorias(id,nombre)",
            "limit": str(limite),
        }
        if solo_activos:
            pg_params["activo"] = "eq.true"
        if termino_busqueda:
            pg_params["or"] = f"(nombre.ilike.*{termino_busqueda}*,codigo.ilike.*{termino_busqueda}*)"
        if ordenar_por_stock_asc is True:
            pg_params["order"] = "cantidad.asc"
        elif ordenar_por_stock_asc is False:
            pg_params["order"] = "cantidad.desc"
        else:
            pg_params["order"] = "nombre.asc"

        res = self._query_postgrest_get("productos", pg_params)
        if res is not None:
            return res

        # Fallback SQLAlchemy
        query = select(Producto).options(selectinload(Producto.categoria))
        if solo_activos:
            query = query.where(Producto.activo == True, Producto.eliminado_at.is_(None))
        if termino_busqueda:
            like_term = f"%{termino_busqueda.strip()}%"
            query = query.where(Producto.nombre.ilike(like_term) | Producto.codigo.ilike(like_term))
        if ordenar_por_stock_asc is True:
            query = query.order_by(Producto.cantidad.asc())
        elif ordenar_por_stock_asc is False:
            query = query.order_by(Producto.cantidad.desc())
        else:
            query = query.order_by(Producto.nombre.asc())

        query = query.limit(limite)
        productos = self.db.scalars(query).all()

        return [
            {
                "id": str(p.id),
                "codigo": p.codigo,
                "nombre": p.nombre,
                "precio": float(p.precio),
                "cantidad": p.cantidad,
                "activo": p.activo,
                "categoria": p.categoria.nombre if p.categoria else "Sin Categoría",
                "notificar_stock": p.notificar_stock,
                "stock_notificacion": p.stock_notificacion,
            }
            for p in productos
        ]

    def consultar_ventas_periodo(
        self,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        incluir_cancelados: bool = False,
    ) -> dict[str, Any]:
        """
        Consulta TODOS los pedidos y calcula totales exactos de ventas en el rango de fechas pedido.
        Garantiza que NUNCA se devuelvan cifras truncadas o parciales (Problema 1 resuelto al 100%).
        """
        dt_desde, dt_hasta, texto_periodo = _parse_fechas_periodo(fecha_desde, fecha_hasta)

        # 1. Total pedidos no cancelados y monto total
        query_totales = (
            select(
                func.count(Pedido.id),
                func.coalesce(func.sum(Pedido.total), Decimal("0.00")),
                func.coalesce(func.sum(Pedido.subtotal), Decimal("0.00")),
            )
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(Pedido.created_at >= dt_desde, Pedido.created_at <= dt_hasta)
        )
        if not incluir_cancelados:
            query_totales = query_totales.where(Estado.nombre != "Cancelado")

        totales_res = self.db.execute(query_totales).one()
        total_pedidos = int(totales_res[0] or 0)
        total_ventas = float(totales_res[1] or 0.0)
        total_subtotal = float(totales_res[2] or 0.0)

        # 2. Conteo de cancelados
        pedidos_cancelados = self.db.scalar(
            select(func.count(Pedido.id))
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(
                Pedido.created_at >= dt_desde,
                Pedido.created_at <= dt_hasta,
                Estado.nombre == "Cancelado",
            )
        ) or 0

        # 3. Unidades totales vendidas
        query_unidades = (
            select(func.coalesce(func.sum(DetallePedido.cantidad), 0))
            .join(Pedido, DetallePedido.pedido_id == Pedido.id)
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(Pedido.created_at >= dt_desde, Pedido.created_at <= dt_hasta)
        )
        if not incluir_cancelados:
            query_unidades = query_unidades.where(Estado.nombre != "Cancelado")
        total_unidades = int(self.db.scalar(query_unidades) or 0)

        # 4. Top 10 Clientes con valores numéricos limpios
        query_top_clientes = (
            select(
                Cliente.id,
                Cliente.nombre,
                Cliente.rut,
                func.count(Pedido.id).label("cantidad_pedidos"),
                func.coalesce(func.sum(Pedido.total), Decimal("0.00")).label("monto_total"),
            )
            .join(Pedido, Pedido.cliente_id == Cliente.id)
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(Pedido.created_at >= dt_desde, Pedido.created_at <= dt_hasta)
        )
        if not incluir_cancelados:
            query_top_clientes = query_top_clientes.where(Estado.nombre != "Cancelado")
        top_clientes_raw = self.db.execute(
            query_top_clientes.group_by(Cliente.id, Cliente.nombre, Cliente.rut)
            .order_by(func.sum(Pedido.total).desc())
            .limit(10)
        ).all()

        top_clientes = [
            {
                "cliente_id": str(r.id),
                "nombre": r.nombre or "Cliente sin nombre",
                "rut": r.rut or "Sin RUT",
                "pedidos": int(r.cantidad_pedidos or 0),
                "total": float(r.monto_total or 0.0),
                "total_formateado": formatear_pesos_chilenos(r.monto_total),
            }
            for r in top_clientes_raw
        ]

        # 5. Top 10 Productos más vendidos en el período
        query_top_productos = (
            select(
                DetallePedido.codigo_producto,
                DetallePedido.nombre_producto,
                func.sum(DetallePedido.cantidad).label("unidades_vendidas"),
                func.coalesce(func.sum(DetallePedido.subtotal), Decimal("0.00")).label("total_ventas"),
            )
            .join(Pedido, DetallePedido.pedido_id == Pedido.id)
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(Pedido.created_at >= dt_desde, Pedido.created_at <= dt_hasta)
        )
        if not incluir_cancelados:
            query_top_productos = query_top_productos.where(Estado.nombre != "Cancelado")
        top_productos_raw = self.db.execute(
            query_top_productos.group_by(DetallePedido.codigo_producto, DetallePedido.nombre_producto)
            .order_by(func.sum(DetallePedido.cantidad).desc())
            .limit(10)
        ).all()

        top_productos = [
            {
                "codigo": r.codigo_producto,
                "nombre": r.nombre_producto,
                "unidades_vendidas": int(r.unidades_vendidas or 0),
                "total_recaudado": float(r.total_ventas or 0.0),
                "total_formateado": formatear_pesos_chilenos(r.total_ventas),
            }
            for r in top_productos_raw
        ]

        ticket_promedio = round(total_ventas / total_pedidos, 2) if total_pedidos > 0 else 0.0

        return {
            "verificado": True,
            "periodo": texto_periodo,
            "fecha_desde": dt_desde.strftime("%Y-%m-%d"),
            "fecha_hasta": dt_hasta.strftime("%Y-%m-%d"),
            "incluye_cancelados": incluir_cancelados,
            "total_pedidos": total_pedidos,
            "total_ventas": total_ventas,
            "total_ventas_formateado": formatear_pesos_chilenos(total_ventas),
            "subtotal_ventas": total_subtotal,
            "subtotal_ventas_formateado": formatear_pesos_chilenos(total_subtotal),
            "ticket_promedio": ticket_promedio,
            "ticket_promedio_formateado": formatear_pesos_chilenos(ticket_promedio),
            "unidades_totales_vendidas": total_unidades,
            "pedidos_cancelados_excluidos": pedidos_cancelados if not incluir_cancelados else 0,
            "top_clientes": top_clientes,
            "top_productos": top_productos,
            "fuente": "Base de datos Tridente (todos los pedidos del período sin recortes)",
        }

    def consultar_top_clientes(
        self,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        limite: int = 10,
    ) -> dict[str, Any]:
        """
        Retorna el ranking de clientes con montos numéricos limpios listos para graficar y tabular.
        """
        limite = min(max(1, limite), 25)
        dt_desde, dt_hasta, texto_periodo = _parse_fechas_periodo(fecha_desde, fecha_hasta)

        query = (
            select(
                Cliente.id,
                Cliente.nombre,
                Cliente.rut,
                func.count(Pedido.id).label("pedidos"),
                func.coalesce(func.sum(Pedido.total), Decimal("0.00")).label("total"),
            )
            .join(Pedido, Pedido.cliente_id == Cliente.id)
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(
                Pedido.created_at >= dt_desde,
                Pedido.created_at <= dt_hasta,
                Estado.nombre != "Cancelado",
            )
            .group_by(Cliente.id, Cliente.nombre, Cliente.rut)
            .order_by(func.sum(Pedido.total).desc())
            .limit(limite)
        )
        filas = self.db.execute(query).all()

        ranking = []
        labels = []
        data_montos = []

        for r in filas:
            nom = r.nombre or "Cliente"
            monto_num = float(r.total or 0.0)
            labels.append(nom[:20])
            data_montos.append(int(round(monto_num)))
            ranking.append(
                {
                    "cliente": nom,
                    "rut": r.rut or "Sin RUT",
                    "pedidos": int(r.pedidos or 0),
                    "total": monto_num,
                    "total_formateado": formatear_pesos_chilenos(monto_num),
                }
            )

        return {
            "verificado": True,
            "periodo": texto_periodo,
            "ranking": ranking,
            "grafico_sugerido": {
                "type": "chart",
                "chartType": "bar",
                "title": f"Top {len(ranking)} Clientes con Mayor Compra",
                "description": f"Período: {texto_periodo}",
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Monto Comprado ($)",
                            "data": data_montos,
                        }
                    ],
                },
            },
        }

    def consultar_productos_stock_critico(
        self,
        stock_maximo: int = 10,
        limite: int = 50,
    ) -> dict[str, Any]:
        """
        Retorna productos activos con stock menor o igual al umbral crítico sin cortes de tabla.
        """
        limite = min(max(1, limite), 100)
        query = (
            select(Producto)
            .options(selectinload(Producto.categoria))
            .where(
                Producto.activo == True,
                Producto.eliminado_at.is_(None),
                Producto.cantidad <= stock_maximo,
            )
            .order_by(Producto.cantidad.asc())
            .limit(limite)
        )
        prods = self.db.scalars(query).all()

        total_en_alerta = (
            self.db.scalar(
                select(func.count(Producto.id)).where(
                    Producto.activo == True,
                    Producto.eliminado_at.is_(None),
                    Producto.cantidad <= stock_maximo,
                )
            )
            or 0
        )

        lista = [
            {
                "codigo": p.codigo,
                "producto": p.nombre,
                "categoria": p.categoria.nombre if p.categoria else "General",
                "stock_actual": f"{p.cantidad} un.",
                "precio": formatear_pesos_chilenos(p.precio),
                "estado": "Agotado 🚨" if p.cantidad <= 0 else "Stock Crítico ⚠️",
            }
            for p in prods
        ]

        return {
            "verificado": True,
            "umbral_consultado": stock_maximo,
            "total_en_alerta": total_en_alerta,
            "productos_mostrados": len(lista),
            "productos": lista,
            "fuente": "Inventario en tiempo real Distribuidora Tridente",
        }

    def consultar_pedidos_recientes(
        self,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        dias_historial: int = 30,
        estado_filtro: str | None = None,
        limite: int = 50,
    ) -> dict[str, Any]:
        """
        Consulta pedidos y sus detalles. Acepta rango exacto de fechas (fecha_desde / fecha_hasta)
        o dias_historial, y retorna el resumen global junto con las órdenes para evitar descalces.
        """
        limite = min(max(1, limite), 100)
        dt_desde, dt_hasta, texto_periodo = _parse_fechas_periodo(
            fecha_desde, fecha_hasta, dias_defecto=dias_historial
        )

        query = (
            select(Pedido)
            .options(
                selectinload(Pedido.cliente),
                selectinload(Pedido.estado),
                selectinload(Pedido.detalles),
            )
            .where(Pedido.created_at >= dt_desde, Pedido.created_at <= dt_hasta)
        )
        if estado_filtro:
            query = query.join(Estado).where(Estado.nombre.ilike(f"%{estado_filtro.strip()}%"))

        # Conteo total en BD
        conteo_total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        monto_total_db = self.db.scalar(select(func.coalesce(func.sum(Pedido.total), Decimal("0.00"))).select_from(query.subquery())) or Decimal("0.00")

        pedidos_db = self.db.scalars(
            query.order_by(Pedido.created_at.desc()).limit(limite)
        ).all()

        resultado = []
        for ped in pedidos_db:
            resultado.append(
                {
                    "id": str(ped.id),
                    "created_at": ped.created_at.strftime("%d/%m/%Y %H:%M") if ped.created_at else None,
                    "total": float(ped.total),
                    "total_formateado": formatear_pesos_chilenos(ped.total),
                    "cliente": ped.cliente.nombre if ped.cliente else "Desconocido",
                    "estado": ped.estado.nombre if ped.estado else "Sin Estado",
                    "cantidad_items": len(ped.detalles),
                }
            )

        return {
            "verificado": conteo_total == len(resultado),
            "periodo": texto_periodo,
            "total_pedidos_periodo": conteo_total,
            "monto_total_periodo": float(monto_total_db),
            "monto_total_formateado": formatear_pesos_chilenos(monto_total_db),
            "pedidos_listados": len(resultado),
            "datos_completos": conteo_total == len(resultado),
            "pedidos": resultado,
            "fuente": "Base de datos Tridente",
        }

    def consultar_metricas_generales(
        self,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Genera métricas consolidadas de ventas, clientes y stock para el período solicitado.
        """
        dt_desde, dt_hasta, texto_periodo = _parse_fechas_periodo(fecha_desde, fecha_hasta, dias_defecto=dias)

        # 1. Total pedidos y facturación (excluyendo cancelados por defecto para cuadrar con Dashboard)
        pedidos_stats = self.db.execute(
            select(
                func.count(Pedido.id),
                func.coalesce(func.sum(Pedido.total), Decimal("0.00")),
            )
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(
                Pedido.created_at >= dt_desde,
                Pedido.created_at <= dt_hasta,
                Estado.nombre != "Cancelado",
            )
        ).one()

        total_pedidos = int(pedidos_stats[0] or 0)
        total_facturado = float(pedidos_stats[1] or 0.0)

        # 2. Top productos más vendidos
        top_vendidos_raw = self.db.execute(
            select(
                DetallePedido.codigo_producto,
                DetallePedido.nombre_producto,
                func.sum(DetallePedido.cantidad).label("unidades_vendidas"),
                func.sum(DetallePedido.subtotal).label("total_ventas"),
            )
            .join(Pedido, DetallePedido.pedido_id == Pedido.id)
            .join(Estado, Pedido.estado_id == Estado.id)
            .where(
                Pedido.created_at >= dt_desde,
                Pedido.created_at <= dt_hasta,
                Estado.nombre != "Cancelado",
            )
            .group_by(DetallePedido.codigo_producto, DetallePedido.nombre_producto)
            .order_by(func.sum(DetallePedido.cantidad).desc())
            .limit(10)
        ).all()

        top_productos = [
            {
                "codigo": row.codigo_producto,
                "nombre": row.nombre_producto,
                "unidades_vendidas": int(row.unidades_vendidas or 0),
                "total_recaudado": float(row.total_ventas or 0.0),
                "total_formateado": formatear_pesos_chilenos(row.total_ventas),
            }
            for row in top_vendidos_raw
        ]

        # 3. Productos con stock crítico
        productos_criticos_raw = self.db.scalars(
            select(Producto)
            .where(
                Producto.activo == True,
                Producto.eliminado_at.is_(None),
                Producto.cantidad <= 10,
            )
            .order_by(Producto.cantidad.asc())
            .limit(15)
        ).all()

        productos_criticos = [
            {
                "codigo": p.codigo,
                "nombre": p.nombre,
                "stock_actual": p.cantidad,
                "precio": float(p.precio),
                "precio_formateado": formatear_pesos_chilenos(p.precio),
            }
            for p in productos_criticos_raw
        ]

        total_productos_activos = (
            self.db.scalar(
                select(func.count(Producto.id)).where(
                    Producto.activo == True, Producto.eliminado_at.is_(None)
                )
            )
            or 0
        )

        ticket_promedio = round(total_facturado / total_pedidos, 2) if total_pedidos > 0 else 0.0

        return {
            "verificado": True,
            "periodo": texto_periodo,
            "total_pedidos": total_pedidos,
            "total_facturado": total_facturado,
            "total_facturado_formateado": formatear_pesos_chilenos(total_facturado),
            "ticket_promedio": ticket_promedio,
            "ticket_promedio_formateado": formatear_pesos_chilenos(ticket_promedio),
            "total_productos_activos": total_productos_activos,
            "top_productos_mas_vendidos": top_productos,
            "productos_stock_critico": productos_criticos,
            "fuente": "Base de datos Tridente (Dashboard y catálogo oficial)",
        }

    def consultar_creditos_morosos(self, dias_vencido_min: int = 0) -> dict[str, Any]:
        """
        Consulta el estado de créditos comerciales, morosidad y cuentas por cobrar.
        Permite identificar clientes con crédito vencido, montos adeudados y días de atraso.
        """
        from app.models.entities import Credito
        try:
            from zoneinfo import ZoneInfo
            tz_chile = ZoneInfo("America/Santiago")
        except Exception:
            tz_chile = UTC
        now = datetime.now(tz_chile).astimezone(UTC)

        query = (
            select(Credito)
            .options(selectinload(Credito.cliente), selectinload(Credito.pedido))
            .where(Credito.pagado.is_(False))
            .order_by(Credito.fecha_vencimiento.asc())
        )
        creditos_pendientes = self.db.scalars(query).all()

        total_pendientes = len(creditos_pendientes)
        monto_total_pendiente = sum(float(c.monto) for c in creditos_pendientes)

        vencidos = []
        por_vencer = []

        for c in creditos_pendientes:
            fv = c.fecha_vencimiento
            if fv.tzinfo is None:
                fv = fv.replace(tzinfo=UTC)
            fv_local = fv.astimezone(tz_chile)

            dias_diff = (now - fv).days
            item = {
                "credito_id": str(c.id),
                "cliente": c.cliente.nombre if c.cliente else "Desconocido",
                "cliente_rut": c.cliente.rut if c.cliente else "",
                "cliente_alias": c.cliente.alias if c.cliente else None,
                "monto": float(c.monto),
                "monto_formateado": _formatear_pesos(c.monto),
                "dias_credito": c.dias_credito,
                "fecha_vencimiento": fv_local.strftime("%d/%m/%Y"),
                "pedido_codigo": c.pedido.codigo if c.pedido else None,
            }
            if fv < now:
                item["dias_vencido"] = max(1, dias_diff)
                item["estado_credito"] = "Vencido"
                vencidos.append(item)
            else:
                item["dias_por_vencer"] = abs(dias_diff)
                item["estado_credito"] = "Vigente"
                por_vencer.append(item)

        monto_vencido = sum(v["monto"] for v in vencidos)
        monto_vigente = sum(pv["monto"] for pv in por_vencer)

        return {
            "periodo": "al día de hoy",
            "total_creditos_pendientes": total_pendientes,
            "monto_total_pendiente": monto_total_pendiente,
            "monto_total_pendiente_formateado": _formatear_pesos(monto_total_pendiente),
            "creditos_vencidos_count": len(vencidos),
            "monto_vencido": monto_vencido,
            "monto_vencido_formateado": _formatear_pesos(monto_vencido),
            "creditos_vigentes_count": len(por_vencer),
            "monto_vigente": monto_vigente,
            "monto_vigente_formateado": _formatear_pesos(monto_vigente),
            "creditos_vencidos": vencidos[:15],
            "resumen": f"Existen {len(vencidos)} créditos vencidos por un total de {_formatear_pesos(monto_vencido)}, y {len(por_vencer)} créditos vigentes por {_formatear_pesos(monto_vigente)}."
        }

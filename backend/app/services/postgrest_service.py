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

    def consultar_pedidos_recientes(
        self,
        dias_historial: int = 30,
        estado_filtro: str | None = None,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Consulta pedidos y sus detalles vía PostgREST GET /pedidos (o fallback BD).
        """
        limite = min(max(1, limite), 100)
        dias = min(max(1, dias_historial), 180)
        fecha_desde = datetime.now(UTC) - timedelta(days=dias)

        pg_params: dict[str, Any] = {
            "select": "id,total,subtotal,created_at,cliente:clientes(id,nombre,rut),estado:estados(id,nombre),detalles:detalle_pedidos(id,producto_id,codigo_producto,nombre_producto,cantidad,precio_unitario,subtotal)",
            "created_at": f"gte.{fecha_desde.isoformat()}",
            "order": "created_at.desc",
            "limit": str(limite),
        }
        if estado_filtro:
            pg_params["estado.nombre"] = f"eq.{estado_filtro}"

        res = self._query_postgrest_get("pedidos", pg_params)
        if res is not None:
            return res

        # Fallback SQLAlchemy
        query = (
            select(Pedido)
            .options(
                selectinload(Pedido.cliente),
                selectinload(Pedido.estado),
                selectinload(Pedido.detalles),
            )
            .where(Pedido.created_at >= fecha_desde)
            .order_by(Pedido.created_at.desc())
            .limit(limite)
        )
        pedidos = self.db.scalars(query).all()

        resultado = []
        for ped in pedidos:
            resultado.append(
                {
                    "id": str(ped.id),
                    "created_at": ped.created_at.isoformat() if ped.created_at else None,
                    "total": float(ped.total),
                    "subtotal": float(ped.subtotal),
                    "cliente": ped.cliente.nombre if ped.cliente else "Desconocido",
                    "estado": ped.estado.nombre if ped.estado else "Sin Estado",
                    "detalles": [
                        {
                            "producto_id": str(d.producto_id),
                            "codigo": d.codigo_producto,
                            "nombre": d.nombre_producto,
                            "cantidad": d.cantidad,
                            "precio_unitario": float(d.precio_unitario),
                            "subtotal": float(d.subtotal),
                        }
                        for d in ped.detalles
                    ],
                }
            )
        return resultado

    def consultar_metricas_generales(self, dias: int = 30) -> dict[str, Any]:
        """
        Genera métricas consolidadas de ventas y stock para alimentar análisis y predicciones.
        """
        fecha_desde = datetime.now(UTC) - timedelta(days=dias)

        # 1. Total pedidos y facturación
        pedidos_stats = self.db.execute(
            select(
                func.count(Pedido.id),
                func.coalesce(func.sum(Pedido.total), Decimal("0.00")),
            ).where(Pedido.created_at >= fecha_desde)
        ).one()

        total_pedidos = pedidos_stats[0] or 0
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
            .where(Pedido.created_at >= fecha_desde)
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
            }
            for row in top_vendidos_raw
        ]

        # 3. Productos con bajo stock o stock crítico
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
            }
            for p in productos_criticos_raw
        ]

        # 4. Total productos activos en catálogo
        total_productos_activos = (
            self.db.scalar(
                select(func.count(Producto.id)).where(
                    Producto.activo == True, Producto.eliminado_at.is_(None)
                )
            )
            or 0
        )

        return {
            "periodo_dias": dias,
            "total_pedidos": total_pedidos,
            "total_facturado": total_facturado,
            "ticket_promedio": round(total_facturado / total_pedidos, 2) if total_pedidos > 0 else 0.0,
            "total_productos_activos": total_productos_activos,
            "top_productos_mas_vendidos": top_productos,
            "productos_stock_critico": productos_criticos,
        }

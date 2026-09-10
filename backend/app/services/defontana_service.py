import logging
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Token en memoria para reutilizar entre llamadas
_CACHED_TOKEN: str | None = None
_TOKEN_EXPIRES_AT: float = 0.0
_TOKEN_LOCK = threading.Lock()


class DefontanaService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (self.settings.defontana_api_base_url or "https://replapi.defontana.com").rstrip("/")
        self.client_id = self.settings.defontana_client_id
        self.company_id = self.settings.defontana_company_id
        self.user = self.settings.defontana_api_user
        self.password = self.settings.defontana_api_password

    def is_configured(self) -> bool:
        return bool(self.client_id and self.company_id and self.user and self.password)

    def get_token(self, force_refresh: bool = False) -> str:
        """Obtiene un token válido desde Defontana o del caché en memoria."""
        global _CACHED_TOKEN, _TOKEN_EXPIRES_AT

        now = time.time()
        with _TOKEN_LOCK:
            if not force_refresh and _CACHED_TOKEN and now < _TOKEN_EXPIRES_AT:
                return _CACHED_TOKEN

            params = {
                "client": self.client_id,
                "company": self.company_id,
                "user": self.user,
                "password": self.password,
            }
            url = f"{self.base_url}/api/Auth"
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            token = data.get("access_token")
            if not token:
                raise ValueError(f"Defontana no retornó access_token: {data}")

            expires_in = data.get("expires_in", 31535999)
            _CACHED_TOKEN = token
            # Renovar 1 hora antes de expirar
            _TOKEN_EXPIRES_AT = now + max(60, expires_in - 3600)
            return token

    def _get_headers(self) -> dict[str, str]:
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def resolve_client(self, rut: str) -> dict[str, Any] | None:
        """
        Busca un cliente por RUT en Defontana.
        Intenta sin puntos (ej: 76294890-7) y luego con puntos (ej: 76.294.890-7).
        """
        if not rut:
            return None

        # Limpiar y preparar formatos
        clean = rut.strip().upper().replace(" ", "")
        rut_no_dots = clean.replace(".", "")
        
        # Calcular formato con puntos
        parts = rut_no_dots.split("-")
        if len(parts) == 2:
            body, dv = parts
            formatted_body = ""
            for i, ch in enumerate(reversed(body)):
                if i > 0 and i % 3 == 0:
                    formatted_body = "." + formatted_body
                formatted_body = ch + formatted_body
            rut_with_dots = f"{formatted_body}-{dv}"
        else:
            rut_with_dots = clean

        candidates = [rut_no_dots, rut_with_dots] if rut_no_dots != rut_with_dots else [rut_no_dots]

        for code in candidates:
            try:
                url = f"{self.base_url}/api/Sale/GetClients"
                params = {
                    "legalCode": code,
                    "status": 0,
                    "pageNumber": 1,
                    "itemsPerPage": 5,
                }
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(url, params=params, headers=self._get_headers())
                    if resp.status_code == 401:
                        # Reintentar refrescando el token
                        resp = client.get(url, params=params, headers={"Authorization": f"Bearer {self.get_token(force_refresh=True)}", "Accept": "application/json"})
                    resp.raise_for_status()
                    data = resp.json()

                client_list = data.get("clientList") or []
                if client_list:
                    return client_list[0]
            except Exception as e:
                logger.warning("Error buscando cliente con RUT %s en Defontana: %s", code, e)

    def create_client(self, cliente: Any, direccion: Any = None) -> dict[str, Any] | None:
        """
        Registra un cliente en Defontana mediante POST /api/Sale/SaveClient.
        Acepta un modelo Cliente (o dict/SimpleNamespace) y opcionalmente Direccion.
        Retorna los datos del cliente creado o None si la API falla.
        """
        if not cliente:
            return None

        rut = getattr(cliente, "rut", None) or (cliente.get("rut") if isinstance(cliente, dict) else None)
        if not rut:
            logger.warning("No se puede registrar cliente en Defontana sin RUT.")
            return None

        # Limpiar y formatear RUT
        clean = str(rut).strip().upper().replace(" ", "")
        rut_no_dots = clean.replace(".", "")
        parts = rut_no_dots.split("-")
        if len(parts) == 2:
            body, dv = parts
            formatted_body = ""
            for i, ch in enumerate(reversed(body)):
                if i > 0 and i % 3 == 0:
                    formatted_body = "." + formatted_body
                formatted_body = ch + formatted_body
            rut_formatted = f"{formatted_body}-{dv}"
        else:
            rut_formatted = clean

        name = (
            getattr(cliente, "nombre", None)
            or (cliente.get("nombre") if isinstance(cliente, dict) else None)
            or f"Cliente {rut_formatted}"
        )
        email = (
            getattr(cliente, "correo", None)
            or (cliente.get("correo") if isinstance(cliente, dict) else None)
            or ""
        )

        addr_str = ""
        district_str = ""
        if direccion:
            addr_str = getattr(direccion, "direccion", None) or (direccion.get("direccion") if isinstance(direccion, dict) else "")
            district_str = getattr(direccion, "comuna", None) or (direccion.get("comuna") if isinstance(direccion, dict) else "")

        address = addr_str or "Sin Dirección"
        district = district_str or "Santiago"
        city = district_str or "Santiago"

        payload = {
            "legalCode": rut_formatted,
            "fileid": rut_formatted,
            "name": str(name)[:100],
            "address": str(address)[:100],
            "district": str(district)[:50],
            "city": str(city)[:50],
            "email": str(email)[:100],
            "business": "Particular",
            "giro": "Particular",
            "rubroId": "1",
            "customFields": [],
        }

        url = f"{self.base_url}/api/Sale/SaveClient"
        headers = self._get_headers()
        try:
            with httpx.Client(timeout=20.0) as client_http:
                resp = client_http.post(url, json=payload, headers=headers)
                if resp.status_code == 401:
                    headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                    resp = client_http.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            success = data.get("success", False)
            msg = data.get("message") or data.get("exceptionMessage")
            if success:
                logger.info("Cliente %s (%s) creado exitosamente en Defontana: %s", rut_formatted, name, msg)
                return {
                    "fileID": rut_formatted,
                    "legalCode": rut_formatted,
                    "name": name,
                    "success": True,
                }
            else:
                logger.warning("Defontana respondió no exitoso al crear cliente %s: %s", rut_formatted, msg)
                return self.resolve_client(rut_formatted)
        except Exception as e:
            logger.exception("Error al crear cliente con RUT %s en Defontana: %s", rut_formatted, e)
            return None

    def resolve_product(self, code: str) -> dict[str, Any] | None:
        """Busca un producto por su código en Defontana."""
        if not code:
            return None
        try:
            url = f"{self.base_url}/api/Sale/Getproducts"
            params = {
                "code": str(code).strip(),
                "status": 0,
                "pageNumber": 1,
                "itemsPerPage": 5,
            }
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params, headers=self._get_headers())
                if resp.status_code == 401:
                    resp = client.get(url, params=params, headers={"Authorization": f"Bearer {self.get_token(force_refresh=True)}", "Accept": "application/json"})
                resp.raise_for_status()
                data = resp.json()

            prod_list = data.get("productList") or []
            if prod_list:
                return prod_list[0]
        except Exception as e:
            logger.warning("Error buscando producto con código %s en Defontana: %s", code, e)

        return None

    def save_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía el pedido a SaveOrder en Defontana."""
        url = f"{self.base_url}/api/Order/SaveOrder"
        headers = self._get_headers()
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def sync_order(self, order_id: UUID) -> tuple[int | None, str | None]:
        """
        Carga el pedido desde la base de datos, resuelve cliente y productos,
        y lo registra en Defontana.
        Retorna (folio, None) en caso de éxito, o (None, error_mensaje) en caso de fallo.
        """
        if not self.is_configured():
            logger.info("Defontana API no está configurada en .env; omitiendo sincronización.")
            return None, "Defontana no configurada"

        from app.core.database import SessionLocal
        from app.models.entities import DetallePedido, Pedido, Producto

        with SessionLocal() as session:
            order = session.scalar(
                select(Pedido)
                .options(
                    selectinload(Pedido.cliente),
                    selectinload(Pedido.direccion),
                    selectinload(Pedido.detalles).selectinload(DetallePedido.producto),
                )
                .where(Pedido.id == order_id)
            )
            if not order:
                return None, f"Pedido {order_id} no encontrado"

            def _is_afecto(item: Any) -> bool:
                # 1. Si producto está cargado en el item
                if getattr(item, "producto", None) is not None and getattr(item.producto, "afecto", None) is not None:
                    return bool(item.producto.afecto)
                # 2. Si no es DetallePedido (ej. DTO o SimpleNamespace de prueba con afecto explícito)
                if not isinstance(item, DetallePedido) and getattr(item, "afecto", None) is not None:
                    return bool(item.afecto)
                # 3. Fallback a BD por producto_id
                if getattr(item, "producto_id", None):
                    p = session.get(Producto, item.producto_id)
                    if p is not None and getattr(p, "afecto", None) is not None:
                        return bool(p.afecto)
                # 4. Fallback a BD por codigo_producto
                prod_c = getattr(item, "codigo_producto", None)
                if prod_c:
                    p = session.scalar(select(Producto).where(Producto.codigo == str(prod_c)))
                    if p is not None and getattr(p, "afecto", None) is not None:
                        return bool(p.afecto)
                # 5. Atributo afecto general en el item si existe
                if getattr(item, "afecto", None) is not None:
                    return bool(item.afecto)
                return False

            client_data = None
            if order.cliente and order.cliente.rut:
                client_data = self.resolve_client(order.cliente.rut)
                if not client_data:
                    logger.info(
                        "Cliente RUT %s no encontrado en Defontana. Registrando cliente automáticamente...",
                        order.cliente.rut,
                    )
                    created_data = self.create_client(order.cliente, order.direccion)
                    if created_data:
                        resolved = self.resolve_client(order.cliente.rut)
                        client_data = resolved or created_data

            client_file_id = (
                (client_data.get("fileID") if client_data else None)
                or (order.cliente.nombre if order.cliente else None)
                or "CLIENTE WEB"
            )
            seller_file_id = (client_data.get("sellerID") if client_data else None) or "VENDEDOR"
            shop_id = (client_data.get("localID") if client_data else None) or "Local"
            payment_condition_id = (client_data.get("paymentID") if client_data else None) or "Contado"

            # Fechas
            try:
                tz = ZoneInfo("America/Santiago")
                now = datetime.now(tz)
            except Exception:
                now = datetime.now()
            
            exp_date = now + timedelta(days=7)

            creation_date = {"day": now.day, "month": now.month, "year": now.year}
            expiration_date = {"day": exp_date.day, "month": exp_date.month, "year": exp_date.year}
            delivery_date = {"day": now.day, "month": now.month, "year": now.year}

            # Helper para armar detalle de producto
            def _build_item_detail(item: Any, is_afecto: bool) -> dict:
                prod_code = item.codigo_producto or ""
                prod_info = self.resolve_product(prod_code) if prod_code else None

                prod_type = (prod_info.get("type") if prod_info else None) or "A"
                prod_name = (prod_info.get("name") if prod_info else None) or item.nombre_producto or f"Producto {prod_code}"
                tipo_empaque = (getattr(item, "tipo_empaque", None) or "unidad").strip().lower()
                cant_caja = getattr(item, "cantidad_caja", None) or (
                    item.producto.cantidad_caja if getattr(item, "producto", None) else None
                )

                price = float(item.precio_unitario)
                count = int(item.cantidad)

                if tipo_empaque == "caja":
                    cant_str = f" x {cant_caja}" if cant_caja else ""
                    comment = f"Presentación: CAJA{cant_str} unid."
                else:
                    comment = "Unidad"

                if is_afecto:
                    tax_obj = {"code": "IVA", "value": 19.0}
                    is_exempt = False
                else:
                    tax_obj = {"code": "", "value": 0.0}
                    is_exempt = True

                return {
                    "type": prod_type,
                    "code": str(prod_code),
                    "productName": prod_name,
                    "unit": "UN",
                    "count": count,
                    "price": price,
                    "comment": comment,
                    "isExempt": is_exempt,
                    "isService": False,
                    "deliveryDate": delivery_date,
                    "deliveryTime": {"hour": 12, "minute": 0},
                    "discount": {"value": 0.0, "type": 1},
                    "tax": tax_obj,
                }

            # Clasificar items entre afectos y exentos
            items_afectos = [it for it in (order.detalles or []) if _is_afecto(it)]
            items_exentos = [it for it in (order.detalles or []) if not _is_afecto(it)]

            if not items_afectos and not items_exentos:
                err_msg = f"Pedido {order_id} no contiene productos para facturar"
                order.defontana_sincronizado = False
                order.defontana_error = err_msg
                session.commit()
                return None, err_msg

            errors = []
            sync_ok = True

            # 1. Factura Electrónica 33 (Afectos) -> documentTypeId = "fvaelect", folio_defontana_afecto
            if items_afectos and not order.folio_defontana_afecto:
                details_afectos = [_build_item_detail(it, is_afecto=True) for it in items_afectos]
                total_afecto = sum(Decimal(str(it.precio_unitario)) * int(it.cantidad) for it in items_afectos)
                iva_value = float(round(total_afecto * Decimal("0.19"), 0))

                gloss_suffix = " - Factura 33 (Afecto)" if items_exentos else " - Factura 33"
                body_afecto = {
                    "documentTypeId": "fvaelect",
                    "clientFileId": str(client_file_id),
                    "sellerFileId": str(seller_file_id),
                    "shopId": str(shop_id),
                    "paymentConditionId": str(payment_condition_id),
                    "billingCoinId": "PESO",
                    "billingRate": 1.0,
                    "creationDate": creation_date,
                    "expirationDate": expiration_date,
                    "glossGeneral": f"Pedido web N° {str(order.id)[:8]}{gloss_suffix}",
                    "taxes": [
                        {
                            "code": "IVA",
                            "value": iva_value,
                        }
                    ],
                    "orderDetails": details_afectos,
                }

                try:
                    res_afecto = self.save_order(body_afecto)
                    if res_afecto.get("success", False) and res_afecto.get("folio"):
                        order.folio_defontana_afecto = int(res_afecto["folio"])
                        logger.info(
                            "Pedido %s: Factura 33 (Afecta) generada con éxito en Defontana con folio %s",
                            order_id,
                            res_afecto["folio"],
                        )
                    else:
                        err_msg = (
                            res_afecto.get("message")
                            or res_afecto.get("exceptionMessage")
                            or f"Error al emitir Factura 33: {res_afecto}"
                        )
                        errors.append(f"Factura 33: {err_msg}")
                        sync_ok = False
                except Exception as exc:
                    errors.append(f"Factura 33 ({type(exc).__name__}): {exc}")
                    sync_ok = False

            # 2. Factura No Afecta o Exenta Electrónica 34 (Exentos) -> documentTypeId = "fveelect", folio_defontana
            if items_exentos and not order.folio_defontana:
                details_exentos = [_build_item_detail(it, is_afecto=False) for it in items_exentos]

                gloss_suffix = " - Factura 34 (Exento)" if items_afectos else " - Factura 34"
                body_exento = {
                    "documentTypeId": "fveelect",
                    "clientFileId": str(client_file_id),
                    "sellerFileId": str(seller_file_id),
                    "shopId": str(shop_id),
                    "paymentConditionId": str(payment_condition_id),
                    "billingCoinId": "PESO",
                    "billingRate": 1.0,
                    "creationDate": creation_date,
                    "expirationDate": expiration_date,
                    "glossGeneral": f"Pedido web N° {str(order.id)[:8]}{gloss_suffix}",
                    "taxes": [],
                    "orderDetails": details_exentos,
                }

                try:
                    res_exento = self.save_order(body_exento)
                    if res_exento.get("success", False) and res_exento.get("folio"):
                        order.folio_defontana = int(res_exento["folio"])
                        logger.info(
                            "Pedido %s: Factura 34 (Exenta) generada con éxito en Defontana con folio %s",
                            order_id,
                            res_exento["folio"],
                        )
                    else:
                        err_msg = (
                            res_exento.get("message")
                            or res_exento.get("exceptionMessage")
                            or f"Error al emitir Factura 34: {res_exento}"
                        )
                        errors.append(f"Factura 34: {err_msg}")
                        sync_ok = False
                except Exception as exc:
                    errors.append(f"Factura 34 ({type(exc).__name__}): {exc}")
                    sync_ok = False

            # Actualizar estado del pedido
            primary_folio = order.folio_defontana_afecto or order.folio_defontana
            if sync_ok and not errors:
                order.defontana_sincronizado = True
                order.defontana_error = None
                session.commit()
                return primary_folio, None
            else:
                combined_err = " | ".join(errors)
                order.defontana_sincronizado = False
                order.defontana_error = combined_err
                session.commit()
                logger.warning("Fallo sincronización Defontana para pedido %s: %s", order_id, combined_err)
                return primary_folio, combined_err


def dispatch_defontana_order_sync_in_background(order_id: UUID) -> None:
    """Envía la sincronización con Defontana en un hilo independiente para no bloquear la respuesta HTTP."""
    def _runner():
        try:
            service = DefontanaService()
            service.sync_order(order_id)
        except Exception as e:
            logger.exception("Excepción no controlada en sincronización Defontana para pedido %s: %s", order_id, e)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()

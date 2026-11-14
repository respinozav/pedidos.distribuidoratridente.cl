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


def _extract_defontana_error(exc: Exception) -> str:
    """Extrae el mensaje legible retornado por Defontana en caso de fallo HTTP."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            data = exc.response.json()
            if isinstance(data, dict):
                msg = (
                    data.get("message")
                    or data.get("exceptionMessage")
                    or data.get("detail")
                    or data.get("description")
                )
                if not msg and "errors" in data:
                    msg = str(data["errors"])
                if msg:
                    return str(msg)
        except Exception:
            pass
        if exc.response.status_code == 404:
            return "El pedido o endpoint de actualización no fue encontrado en Defontana (HTTP 404). Defontana no permite modificar este documento."
        if exc.response.status_code == 405:
            return "Defontana no admite modificación para este tipo de documento vía API (HTTP 405)."
        if exc.response.text:
            text = exc.response.text.strip()
            if len(text) < 300:
                return text
    return str(exc)


def _is_address_error(err_str: str | None) -> bool:
    """Detecta si un mensaje de error o excepción de Defontana corresponde a error de dirección o sucursal."""
    if not err_str:
        return False
    lower = str(err_str).lower()
    address_keywords = [
        "direcci",
        "direccion",
        "address",
        "despacho",
        "domicilio",
        "sucursal",
        "local",
        "comuna",
        "district",
        "city",
        "ciudad",
    ]
    return any(kw in lower for kw in address_keywords)


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
        city_str = ""
        if direccion:
            addr_str = getattr(direccion, "direccion", None) or (direccion.get("direccion") if isinstance(direccion, dict) else "")
            district_str = getattr(direccion, "comuna", None) or (direccion.get("comuna") if isinstance(direccion, dict) else "")
            city_str = getattr(direccion, "ciudad", None) or (direccion.get("ciudad") if isinstance(direccion, dict) else "")

        address = (addr_str or "Sin Dirección").strip()
        district = (district_str or "Santiago").strip()
        city = (city_str or district_str or "Santiago").strip()

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
        try:
            headers = self._get_headers()
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

    def update_client(self, cliente: Any, direccion: Any = None, client_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """
        Actualiza los datos (especialmente la dirección de despacho y contacto) de un cliente en Defontana
        mediante POST /api/Sale/UpdateClient.
        Asegura que el maestro de clientes en Defontana tenga la dirección seleccionada en el pedido,
        permitiendo que la Guía de Despacho (DTE 52) y Factura (DTE 33/34) se generen con dicha dirección.
        """
        if not cliente:
            return None

        rut = getattr(cliente, "rut", None) or (cliente.get("rut") if isinstance(cliente, dict) else None)
        if not rut:
            logger.warning("No se puede actualizar cliente en Defontana sin RUT.")
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

        file_id = (
            (client_data.get("fileID") if client_data else None)
            or (client_data.get("fileid") if client_data else None)
            or rut_formatted
        )
        name = (
            getattr(cliente, "nombre", None)
            or (cliente.get("nombre") if isinstance(cliente, dict) else None)
            or (client_data.get("name") if client_data else None)
            or f"Cliente {rut_formatted}"
        )
        email = (
            getattr(cliente, "correo", None)
            or (cliente.get("correo") if isinstance(cliente, dict) else None)
            or (client_data.get("email") if client_data else None)
            or ""
        )
        phone = (
            getattr(cliente, "celular", None)
            or (cliente.get("celular") if isinstance(cliente, dict) else None)
            or (client_data.get("phone") if client_data else None)
            or ""
        )

        addr_str = ""
        district_str = ""
        city_str = ""
        if direccion:
            addr_str = getattr(direccion, "direccion", None) or (direccion.get("direccion") if isinstance(direccion, dict) else "")
            district_str = getattr(direccion, "comuna", None) or (direccion.get("comuna") if isinstance(direccion, dict) else "")
            city_str = getattr(direccion, "ciudad", None) or (direccion.get("ciudad") if isinstance(direccion, dict) else "")

        # Si no hay dirección en el objeto direccion, usar la previa si existe
        address = (addr_str or (client_data.get("address") if client_data else None) or "Sin Dirección").strip()
        district = (district_str or (client_data.get("district") if client_data else None) or "Santiago").strip()
        city = (city_str or district_str or (client_data.get("city") if client_data else None) or "Santiago").strip()

        business = (client_data.get("business") if client_data else None) or "Particular"
        giro = (client_data.get("giro") if client_data else None) or "Particular"
        rubro_id = (client_data.get("rubroId") if client_data else None) or "1"

        payload = {
            "legalCode": rut_formatted,
            "fileid": str(file_id),
            "name": str(name)[:100],
            "address": str(address)[:100],
            "district": str(district)[:50],
            "city": str(city)[:50],
            "email": str(email)[:100],
            "phone": str(phone)[:30],
            "business": str(business)[:100],
            "giro": str(giro)[:100],
            "rubroId": str(rubro_id),
            "customFields": [],
        }

        url = f"{self.base_url}/api/Sale/UpdateClient"
        try:
            headers = self._get_headers()
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
                logger.info(
                    "Cliente %s (%s) actualizado exitosamente en Defontana con dirección '%s, %s'",
                    rut_formatted,
                    name,
                    address,
                    district,
                )
                return data
            else:
                logger.warning("Defontana respondió no exitoso al actualizar cliente %s: %s", rut_formatted, msg)
                return None
        except Exception as e:
            logger.warning("Error al actualizar cliente con RUT %s en Defontana: %s", rut_formatted, e)
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

    def get_categories(self) -> list[dict[str, Any]]:
        """Obtiene la lista de categorías registradas desde Defontana."""
        url = f"{self.base_url}/api/Sale/GetCategories"
        params = {"pageNumber": 1, "itemsPerPage": 100}
        headers = self._get_headers()
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params, headers=headers)
                if resp.status_code == 401:
                    headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                    resp = client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data.get("categoriesList") or []
        except Exception as e:
            logger.warning("Error obteniendo categorías desde Defontana: %s", e)
            return []

    def _find_category_id(self, category_name: str | None) -> int | None:
        """Busca el ID numérico de categoría en Defontana por nombre."""
        if not category_name:
            return None
        try:
            cats = self.get_categories()
            target = category_name.strip().upper()
            for c in cats:
                desc = (c.get("description") or "").strip().upper()
                if desc == target:
                    return c.get("categoryID")
        except Exception as e:
            logger.warning("Error al buscar ID de categoría '%s' en Defontana: %s", category_name, e)
        return None

    def save_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Registra un producto en Defontana mediante POST /api/Sale/SaveProduct."""
        url = f"{self.base_url}/api/Sale/SaveProduct"
        headers = self._get_headers()
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.post(url, json=payload, headers=headers)
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            resp.raise_for_status()
            return {"success": resp.is_success}

    def update_product_defontana(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Actualiza la información de un producto en Defontana mediante POST /api/Sale/UpdateProduct."""
        url = f"{self.base_url}/api/Sale/UpdateProduct"
        headers = self._get_headers()
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.post(url, json=payload, headers=headers)
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            resp.raise_for_status()
            return {"success": resp.is_success}

    def save_product_price_list(self, price_list_id: float | int, product_code: str, price: float | Decimal) -> dict[str, Any]:
        """Actualiza o agrega un producto en una lista de precios en Defontana."""
        url = f"{self.base_url}/api/Sale/SaveProductPriceList"
        headers = self._get_headers()
        payload = {
            "priceListId": float(price_list_id),
            "productId": str(product_code).strip(),
            "productPrice": float(price),
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.post(url, json=payload, headers=headers)
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            return {"success": resp.is_success}

    def sync_product(
        self,
        code: str,
        name: str,
        price: float | Decimal,
        category_name: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Sincroniza un producto y su precio con Defontana ERP.
        Si el producto ya existe en Defontana, actualiza sus datos y listas de precios asociadas.
        Si no existe, lo crea en Defontana mediante SaveProduct.
        """
        if not self.is_configured():
            return True, None

        code_str = str(code).strip()
        name_str = str(name).strip()[:180]
        price_val = float(price)

        try:
            # 1. Intentar resolver producto existente en Defontana
            existing = self.resolve_product(code_str)

            # 2. Si existe, actualizar con UpdateProduct
            if existing:
                unit = existing.get("unit") or "UN"
                cat_id = existing.get("categoryID")
                if not cat_id and category_name:
                    cat_id = self._find_category_id(category_name)
                id_impto_ad = existing.get("idImptoAd") or existing.get("imptoAd")

                update_payload: dict[str, Any] = {
                    "code": code_str,
                    "name": name_str,
                    "unit": unit,
                    "price": price_val,
                    "description": name_str,
                    "isService": False,
                }
                if cat_id is not None:
                    update_payload["categoryID"] = int(cat_id)
                if id_impto_ad:
                    update_payload["idImptoAd"] = str(id_impto_ad)

                res = self.update_product_defontana(update_payload)
                success = res.get("success", False) if isinstance(res, dict) else False
                msg = (res.get("message") or res.get("exceptionMessage") or "") if isinstance(res, dict) else ""

                # Si falló porque no se encontró, intentar crearlo
                if not success and ("no existe" in msg.lower() or "not found" in msg.lower()):
                    return self._create_product_defontana(code_str, name_str, price_val, category_name)

                if not success:
                    logger.warning("Defontana UpdateProduct falló para código %s: %s", code_str, msg)
                    return False, msg or "Defontana rechazó la actualización del producto"

                # Actualizar también listas de precios asociadas si existen
                price_lists = existing.get("priceListDetail") or []
                for pl in price_lists:
                    pl_id = pl.get("priceListID")
                    if pl_id is None and isinstance(pl.get("priceList"), dict):
                        pl_id = pl["priceList"].get("priceListID")
                    if pl_id is not None:
                        try:
                            self.save_product_price_list(pl_id, code_str, price_val)
                        except Exception as exc:
                            logger.warning(
                                "Error actualizando lista de precios %s para producto %s: %s",
                                pl_id,
                                code_str,
                                exc,
                            )

                logger.info("Producto %s actualizado exitosamente en Defontana con precio %s", code_str, price_val)
                return True, None

            # 3. Si no existe en Defontana, crearlo con SaveProduct
            return self._create_product_defontana(code_str, name_str, price_val, category_name)
        except Exception as e:
            logger.exception("Error al sincronizar producto %s con Defontana: %s", code_str, e)
            if "Login failed" in str(e) or "access_token" in str(e):
                logger.warning("Credenciales de Defontana no operativas en este entorno (%s); omitiendo sincronización de producto.", e)
                return True, None
            return False, str(e)

    def _create_product_defontana(
        self,
        code: str,
        name: str,
        price: float,
        category_name: str | None = None,
    ) -> tuple[bool, str | None]:
        """Crea un producto nuevo en Defontana usando SaveProduct."""
        cat_id = self._find_category_id(category_name) if category_name else None
        save_payload: dict[str, Any] = {
            "code": code,
            "name": name,
            "unit": "UN",
            "price": price,
            "description": name,
            "isService": False,
            "usaLotes": False,
        }
        if cat_id is not None:
            save_payload["categoryID"] = int(cat_id)

        res = self.save_product(save_payload)
        success = res.get("success", False) if isinstance(res, dict) else False
        msg = (res.get("message") or res.get("exceptionMessage") or "") if isinstance(res, dict) else ""

        # Si Defontana dice que ya existe, intentar UpdateProduct
        if not success and ("ya existe" in msg.lower() or "already exists" in msg.lower()):
            update_payload: dict[str, Any] = {
                "code": code,
                "name": name,
                "unit": "UN",
                "price": price,
                "description": name,
                "isService": False,
            }
            if cat_id is not None:
                update_payload["categoryID"] = int(cat_id)
            res2 = self.update_product_defontana(update_payload)
            success2 = res2.get("success", False) if isinstance(res2, dict) else False
            msg2 = (res2.get("message") or res2.get("exceptionMessage") or "") if isinstance(res2, dict) else ""
            if success2:
                logger.info("Producto %s actualizado vía UpdateProduct tras detectar que ya existía", code)
                return True, None
            return False, msg2 or "Defontana rechazó la actualización del producto"

        if not success:
            logger.warning("Defontana SaveProduct falló para código %s: %s", code, msg)
            return False, msg or "Defontana rechazó la creación del producto"

        logger.info("Producto %s creado exitosamente en Defontana con precio %s", code, price)
        return True, None

    ALLOWED_SAVE_ORDER_FIELDS = {
        "documentTypeId",
        "number",
        "pricingId",
        "clientFileId",
        "sellerFileId",
        "referenceNumber",
        "paymentConditionId",
        "billingCoinId",
        "billingRate",
        "shopId",
        "priceListId",
        "billingType",
        "giro",
        "district",
        "address",
        "deliveryAddress",
        "city",
        "dateOrder",
        "orderDetails",
        "taxes",
        "creationDate",
        "expirationDate",
        "glossGeneral",
        "glossDispatch",
        "glossBill",
        "glossPresentation",
        "orderRecDesGlobal",
        "customFields",
    }

    ALLOWED_UPDATE_ORDER_FIELDS = {
        "number",
        "clientFileId",
        "sellerFileId",
        "paymentConditionId",
        "billingCoinId",
        "billingRate",
        "shopId",
        "priceListId",
        "billingType",
        "giro",
        "district",
        "orderDetails",
        "taxes",
        "creationDate",
        "expirationDate",
        "glossGeneral",
        "glossDispatch",
        "glossBill",
        "glossPresentation",
        "orderRecDesGlobal",
        "customFields",
    }

    def get_order(self, number: int | str) -> dict[str, Any]:
        """Consulta la información y líneas de un pedido en Defontana vía GET /api/Order/Get?number={number}."""
        url = f"{self.base_url}/api/Order/Get"
        headers = self._get_headers()
        with httpx.Client(timeout=25.0) as client:
            resp = client.get(url, params={"number": int(number)}, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.get(url, params={"number": int(number)}, headers=headers)
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            resp.raise_for_status()
            return resp.json()

    def delete_order(self, number: int | str) -> dict[str, Any]:
        """Elimina o anula un pedido pendiente en Defontana vía GET /api/Order/Delete?number={number}."""
        url = f"{self.base_url}/api/Order/Delete"
        headers = self._get_headers()
        with httpx.Client(timeout=25.0) as client:
            resp = client.get(url, params={"number": str(number)}, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.get(url, params={"number": str(number)}, headers=headers)
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            resp.raise_for_status()
            return resp.json()

    def save_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía el pedido a SaveOrder en Defontana cumpliendo estrictamente con el esquema OrderInput."""
        url = f"{self.base_url}/api/Order/SaveOrder"
        headers = self._get_headers()
        clean_payload = {k: v for k, v in payload.items() if k in self.ALLOWED_SAVE_ORDER_FIELDS}
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=clean_payload, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.post(url, json=clean_payload, headers=headers)
            try:
                data = resp.json()
                if isinstance(data, dict) and ("success" in data or "message" in data or "exceptionMessage" in data or "errors" in data):
                    return data
            except Exception:
                pass
            resp.raise_for_status()
            return resp.json()

    def update_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía el pedido a UpdateOrder en Defontana cumpliendo estrictamente con el esquema OrderUpdateInput (sin query params)."""
        url = f"{self.base_url}/api/Order/UpdateOrder"
        headers = self._get_headers()
        clean_payload = {k: v for k, v in payload.items() if k in self.ALLOWED_UPDATE_ORDER_FIELDS}
        logger.info(
            "Enviando UpdateOrder a Defontana para folio %s (%d líneas)",
            clean_payload.get("number"),
            len(clean_payload.get("orderDetails", [])),
        )
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=clean_payload, headers=headers)
            if resp.status_code == 401:
                headers["Authorization"] = f"Bearer {self.get_token(force_refresh=True)}"
                resp = client.post(url, json=clean_payload, headers=headers)

            logger.info("Defontana UpdateOrder HTTP %s: %s", resp.status_code, resp.text[:500] if resp.text else "")

            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

            resp.raise_for_status()
            return resp.json()

    def save_or_update_order(self, payload: dict[str, Any], is_update: bool = False) -> dict[str, Any]:
        """
        Envía el pedido a Defontana.
        Si es actualización y tiene folio previo, se comunica con UpdateOrder.
        NUNCA recurre a SaveOrder cuando is_update=True para evitar duplicar
        o crear pedidos adicionales en Defontana cuando se intenta modificar uno existente.
        """
        if is_update:
            return self.update_order(payload)
        return self.save_order(payload)

    def sync_order(
        self,
        order_id: UUID,
        session: Any = None,
        auto_commit: bool = True,
        is_update: bool = False,
    ) -> tuple[int | None, str | None]:
        """
        Carga el pedido desde la base de datos (o la sesión provista), resuelve cliente y productos,
        y lo registra/actualiza en Defontana.
        Retorna (folio, None) en caso de éxito, o (primary_folio, error_mensaje) en caso de fallo.
        """
        if not self.is_configured():
            logger.info("Defontana API no está configurada en .env; omitiendo sincronización.")
            return None, "Defontana no configurada"

        if session is not None:
            return self._sync_order_internal(order_id, session, auto_commit=auto_commit, is_update=is_update)

        from app.core.database import SessionLocal

        with SessionLocal() as local_session:
            return self._sync_order_internal(order_id, local_session, auto_commit=True, is_update=is_update)

    def _sync_order_internal(
        self,
        order_id: UUID,
        session: Any,
        auto_commit: bool = True,
        is_update: bool = False,
    ) -> tuple[int | None, str | None]:
        from app.models.entities import DetallePedido, Pedido, Producto

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

        # Asegurar que order.detalles refleje datos frescos de la BD con productos cargados
        if hasattr(session, "expire") and hasattr(order, "_sa_instance_state"):
            try:
                session.expire(order, ["detalles"])
            except Exception:
                pass
        if hasattr(session, "scalars"):
            try:
                reloaded_detalles = list(
                    session.scalars(
                        select(DetallePedido)
                        .options(selectinload(DetallePedido.producto))
                        .where(DetallePedido.pedido_id == order_id)
                    )
                )
                if reloaded_detalles:
                    order.detalles = reloaded_detalles
            except Exception:
                pass

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

        # Obtener datos de dirección seleccionada para el despacho
        addr_val = ""
        dist_val = ""
        city_val = ""
        if order.direccion:
            addr_val = (getattr(order.direccion, "direccion", None) or "").strip()
            dist_val = (getattr(order.direccion, "comuna", None) or "").strip()
            city_val = (getattr(order.direccion, "ciudad", None) or "").strip()

        dispatch_address = addr_val or "Sin Dirección"
        dispatch_district = dist_val or "Santiago"
        dispatch_city = city_val or dist_val or "Santiago"
        dispatch_full = f"{dispatch_address}, {dispatch_district}" if addr_val else "Sin dirección registrada"

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
            elif order.direccion:
                def_address = (client_data.get("address") or "").strip()
                def_district = (client_data.get("district") or "").strip()

                address_differs = (
                    addr_val and (
                        def_address.lower() != addr_val.lower()
                        or (dist_val and def_district.lower() != dist_val.lower())
                    )
                )

                if address_differs or not def_address or def_address == "Sin Dirección":
                    logger.info(
                        "Dirección de despacho del pedido ('%s, %s') no coincide o no existe en Defontana ('%s, %s') para cliente %s. Actualizando cliente en Defontana...",
                        addr_val,
                        dist_val,
                        def_address,
                        def_district,
                        order.cliente.rut,
                    )
                    try:
                        update_res = self.update_client(order.cliente, order.direccion, client_data=client_data)
                        if update_res:
                            client_data["address"] = dispatch_address
                            client_data["district"] = dispatch_district
                            client_data["city"] = dispatch_city
                    except Exception as exc:
                        logger.warning("No se pudo actualizar la dirección del cliente %s en Defontana: %s", order.cliente.rut, exc)
                else:
                    logger.info(
                        "Cliente RUT %s ya cuenta con la dirección de despacho '%s' en Defontana.",
                        order.cliente.rut,
                        dispatch_full,
                    )

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
            elif not is_afecto:
                # En Factura documento 34 (Exenta), no se debe colocar "Unidad" como comentario en Defontana
                comment = ""
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
        if items_afectos:
            details_afectos = [_build_item_detail(it, is_afecto=True) for it in items_afectos]
            total_afecto = sum(Decimal(str(it.precio_unitario)) * int(it.cantidad) for it in items_afectos)
            iva_value = float(round(total_afecto * Decimal("0.19"), 0))
            expected_count_afecto = sum(int(it.cantidad) for it in items_afectos)

            gloss_suffix = " - Factura 33 (Afecto)" if items_exentos else " - Factura 33"
            gloss_delivery = f" | Despacho: {dispatch_full}" if addr_val else ""
            gloss_dispatch = f"Despacho: {dispatch_full}"[:200]
            body_afecto = {
                "documentTypeId": "fvaelect",
                "clientFileId": str(client_file_id),
                "sellerFileId": str(seller_file_id),
                "shopId": str(shop_id),
                "paymentConditionId": str(payment_condition_id),
                "billingCoinId": "PESO",
                "billingRate": 1.0,
                "creationDate": creation_date,
                "dateOrder": creation_date,
                "expirationDate": expiration_date,
                "district": str(dispatch_district)[:50],
                "address": str(dispatch_address)[:100],
                "deliveryAddress": str(dispatch_address)[:100],
                "city": str(dispatch_city)[:50],
                "glossGeneral": f"Pedido web N° {str(order.id)[:8]}{gloss_suffix}{gloss_delivery}"[:200],
                "glossDispatch": gloss_dispatch,
                "glossBill": f"Pedido web N° {str(order.id)[:8]}{gloss_delivery}"[:200],
                "taxes": [
                    {
                        "code": "IVA",
                        "value": iva_value,
                    }
                ],
                "orderDetails": details_afectos,
            }
            
            has_afecto_folio = bool(order.folio_defontana_afecto)
            is_afecto_update = bool(is_update and has_afecto_folio)

            if is_afecto_update:
                folio_num = int(order.folio_defontana_afecto)
                body_afecto["number"] = folio_num
                body_afecto.pop("documentTypeId", None)

                # Intentar actualización in-place con UpdateOrder
                try:
                    res_afecto = self.update_order(body_afecto)
                    success_afecto = bool(res_afecto.get("success", False) or res_afecto.get("isSuccess", False))
                    needs_recreate = False

                    if success_afecto:
                        # Verificar si Defontana realmente aplicó la actualización de líneas o la ignoró
                        try:
                            get_res = self.get_order(folio_num)
                            order_data = get_res.get("orderData") if isinstance(get_res, dict) else None
                            if order_data and "details" in order_data:
                                remote_details = order_data.get("details") or []
                                remote_count = sum(float(d.get("count", 0)) for d in remote_details)
                                if abs(remote_count - expected_count_afecto) > 0.001:
                                    logger.warning(
                                        "Pedido %s: Defontana UpdateOrder retornó éxito pero no aplicó las líneas (remoto %s vs esperado %s). Procediendo a recreación.",
                                        order_id,
                                        remote_count,
                                        expected_count_afecto,
                                    )
                                    needs_recreate = True
                                else:
                                    logger.info(
                                        "Pedido %s: Modificación in-place en Defontana verificada (Folio %s, Cantidad total %s).",
                                        order_id,
                                        folio_num,
                                        remote_count,
                                    )
                        except Exception as get_err:
                            logger.info("No fue posible verificar líneas con GetOrder (se asume éxito in-place): %s", get_err)
                    if not success_afecto:
                        err_msg = (
                            res_afecto.get("message")
                            or res_afecto.get("exceptionMessage")
                            or res_afecto.get("description")
                            or res_afecto.get("detail")
                            or str(res_afecto)
                        )
                        if _is_address_error(err_msg) and order.direccion:
                            self.update_client(order.cliente, order.direccion, client_data=client_data)
                            res_afecto = self.update_order(body_afecto)
                            success_afecto = bool(res_afecto.get("success", False) or res_afecto.get("isSuccess", False))

                        if not success_afecto:
                            errors.append(f"Factura 33: {err_msg}")
                            sync_ok = False

                    # Si UpdateOrder retornó éxito pero no aplicó las líneas en el ERP, recrear pedido
                    if success_afecto and needs_recreate:
                        logger.info("Pedido %s: Recreando pedido en Defontana para actualizar productos...", order_id)
                        del_res = self.delete_order(folio_num)
                        del_ok = bool(isinstance(del_res, dict) and (del_res.get("success", False) or del_res.get("isSuccess", False)))
                        if not del_ok:
                            del_msg = (del_res.get("message") or del_res.get("exceptionMessage") or str(del_res)) if isinstance(del_res, dict) else str(del_res)
                            errors.append(f"Factura 33: Defontana no permite modificar el pedido #{folio_num}: {del_msg}")
                            sync_ok = False
                        else:
                            body_save = dict(body_afecto)
                            body_save["documentTypeId"] = "fvaelect"
                            body_save.pop("number", None)
                            save_res = self.save_order(body_save)
                            if save_res.get("success", False) or save_res.get("isSuccess", False):
                                new_folio = save_res.get("folio") or save_res.get("number")
                                if new_folio:
                                    order.folio_defontana_afecto = int(new_folio)
                                logger.info(
                                    "Pedido %s: Factura 33 recreada exitosamente en Defontana con folio %s",
                                    order_id,
                                    order.folio_defontana_afecto,
                                )
                            else:
                                save_err = save_res.get("message") or save_res.get("exceptionMessage") or str(save_res)
                                errors.append(f"Factura 33: Error al recrear en Defontana: {save_err}")
                                sync_ok = False
                except Exception as exc:
                    err_msg = _extract_defontana_error(exc)
                    errors.append(f"Factura 33: {err_msg}")
                    sync_ok = False
            else:
                # Creación normal con SaveOrder
                try:
                    res_afecto = self.save_order(body_afecto)
                    success_afecto = bool(res_afecto.get("success", False) or res_afecto.get("isSuccess", False))
                    if success_afecto:
                        new_folio = res_afecto.get("folio") or res_afecto.get("number")
                        if new_folio:
                            order.folio_defontana_afecto = int(new_folio)
                        logger.info(
                            "Pedido %s: Factura 33 generada con éxito en Defontana con folio %s",
                            order_id,
                            order.folio_defontana_afecto,
                        )
                    else:
                        err_msg = (
                            res_afecto.get("message")
                            or res_afecto.get("exceptionMessage")
                            or res_afecto.get("description")
                            or res_afecto.get("detail")
                            or f"Defontana rechazó la creación: {res_afecto}"
                        )
                        if _is_address_error(err_msg) and order.direccion:
                            self.update_client(order.cliente, order.direccion, client_data=client_data)
                            res_afecto = self.save_order(body_afecto)
                            if res_afecto.get("success", False) or res_afecto.get("isSuccess", False):
                                new_folio = res_afecto.get("folio") or res_afecto.get("number")
                                if new_folio:
                                    order.folio_defontana_afecto = int(new_folio)
                                err_msg = None
                        if err_msg:
                            errors.append(f"Factura 33: {err_msg}")
                            sync_ok = False
                except Exception as exc:
                    err_msg = _extract_defontana_error(exc)
                    if _is_address_error(err_msg) and order.direccion:
                        try:
                            self.update_client(order.cliente, order.direccion, client_data=client_data)
                            res_afecto = self.save_order(body_afecto)
                            if res_afecto.get("success", False) or res_afecto.get("isSuccess", False):
                                new_folio = res_afecto.get("folio") or res_afecto.get("number")
                                if new_folio:
                                    order.folio_defontana_afecto = int(new_folio)
                                err_msg = None
                        except Exception as retry_exc:
                            err_msg = _extract_defontana_error(retry_exc)
                    if err_msg:
                        errors.append(f"Factura 33: {err_msg}")
                        sync_ok = False

        # 2. Factura No Afecta o Exenta Electrónica 34 (Exentos) -> documentTypeId = "fveelect", folio_defontana
        if items_exentos:
            details_exentos = [_build_item_detail(it, is_afecto=False) for it in items_exentos]
            expected_count_exento = sum(int(it.cantidad) for it in items_exentos)

            gloss_suffix = " - Factura 34 (Exento)" if items_afectos else " - Factura 34"
            gloss_delivery = f" | Despacho: {dispatch_full}" if addr_val else ""
            gloss_dispatch = f"Despacho: {dispatch_full}"[:200]
            body_exento = {
                "documentTypeId": "fveelect",
                "clientFileId": str(client_file_id),
                "sellerFileId": str(seller_file_id),
                "shopId": str(shop_id),
                "paymentConditionId": str(payment_condition_id),
                "billingCoinId": "PESO",
                "billingRate": 1.0,
                "creationDate": creation_date,
                "dateOrder": creation_date,
                "expirationDate": expiration_date,
                "district": str(dispatch_district)[:50],
                "address": str(dispatch_address)[:100],
                "deliveryAddress": str(dispatch_address)[:100],
                "city": str(dispatch_city)[:50],
                "glossGeneral": f"Pedido web N° {str(order.id)[:8]}{gloss_suffix}{gloss_delivery}"[:200],
                "glossDispatch": gloss_dispatch,
                "glossBill": f"Pedido web N° {str(order.id)[:8]}{gloss_delivery}"[:200],
                "taxes": [],
                "orderDetails": details_exentos,
            }
            
            has_exento_folio = bool(order.folio_defontana)
            is_exento_update = bool(is_update and has_exento_folio)

            if is_exento_update:
                folio_num = int(order.folio_defontana)
                body_exento["number"] = folio_num
                body_exento.pop("documentTypeId", None)

                # Intentar actualización in-place con UpdateOrder
                try:
                    res_exento = self.update_order(body_exento)
                    success_exento = bool(res_exento.get("success", False) or res_exento.get("isSuccess", False))
                    needs_recreate_exento = False

                    if success_exento:
                        # Verificar si Defontana realmente aplicó la actualización de líneas o la ignoró
                        try:
                            get_res = self.get_order(folio_num)
                            order_data = get_res.get("orderData") if isinstance(get_res, dict) else None
                            if order_data and "details" in order_data:
                                remote_details = order_data.get("details") or []
                                remote_count = sum(float(d.get("count", 0)) for d in remote_details)
                                if abs(remote_count - expected_count_exento) > 0.001:
                                    logger.warning(
                                        "Pedido %s: Defontana UpdateOrder (Exento) retornó éxito pero no aplicó las líneas (remoto %s vs esperado %s). Procediendo a recreación.",
                                        order_id,
                                        remote_count,
                                        expected_count_exento,
                                    )
                                    needs_recreate_exento = True
                                else:
                                    logger.info(
                                        "Pedido %s: Modificación in-place Factura 34 en Defontana verificada (Folio %s, Cantidad total %s).",
                                        order_id,
                                        folio_num,
                                        remote_count,
                                    )
                        except Exception as get_err:
                            logger.info("No fue posible verificar líneas Factura 34 con GetOrder (se asume éxito in-place): %s", get_err)
                    if not success_exento:
                        err_msg = (
                            res_exento.get("message")
                            or res_exento.get("exceptionMessage")
                            or res_afecto.get("description")
                            or res_exento.get("detail")
                            or str(res_exento)
                        )
                        if _is_address_error(err_msg) and order.direccion:
                            self.update_client(order.cliente, order.direccion, client_data=client_data)
                            res_exento = self.update_order(body_exento)
                            success_exento = bool(res_exento.get("success", False) or res_exento.get("isSuccess", False))

                        if not success_exento:
                            errors.append(f"Factura 34: {err_msg}")
                            sync_ok = False

                    # Si UpdateOrder retornó éxito pero no aplicó las líneas en el ERP, recrear pedido
                    if success_exento and needs_recreate_exento:
                        logger.info("Pedido %s: Recreando pedido Factura 34 en Defontana para actualizar productos...", order_id)
                        del_res = self.delete_order(folio_num)
                        del_ok = bool(isinstance(del_res, dict) and (del_res.get("success", False) or del_res.get("isSuccess", False)))
                        if not del_ok:
                            del_msg = (del_res.get("message") or del_res.get("exceptionMessage") or str(del_res)) if isinstance(del_res, dict) else str(del_res)
                            errors.append(f"Factura 34: Defontana no permite modificar el pedido #{folio_num}: {del_msg}")
                            sync_ok = False
                        else:
                            body_save = dict(body_exento)
                            body_save["documentTypeId"] = "fveelect"
                            body_save.pop("number", None)
                            save_res = self.save_order(body_save)
                            if save_res.get("success", False) or save_res.get("isSuccess", False):
                                new_folio = save_res.get("folio") or save_res.get("number")
                                if new_folio:
                                    order.folio_defontana = int(new_folio)
                                logger.info(
                                    "Pedido %s: Factura 34 recreada exitosamente en Defontana con folio %s",
                                    order_id,
                                    order.folio_defontana,
                                )
                            else:
                                save_err = save_res.get("message") or save_res.get("exceptionMessage") or str(save_res)
                                errors.append(f"Factura 34: Error al recrear en Defontana: {save_err}")
                                sync_ok = False
                except Exception as exc:
                    err_msg = _extract_defontana_error(exc)
                    errors.append(f"Factura 34: {err_msg}")
                    sync_ok = False
            else:
                # Creación normal Factura 34 con SaveOrder
                try:
                    res_exento = self.save_order(body_exento)
                    success_exento = bool(res_exento.get("success", False) or res_exento.get("isSuccess", False))
                    if success_exento:
                        new_folio = res_exento.get("folio") or res_exento.get("number")
                        if new_folio:
                            order.folio_defontana = int(new_folio)
                        logger.info(
                            "Pedido %s: Factura 34 (Exenta) generada con éxito en Defontana con folio %s",
                            order_id,
                            order.folio_defontana,
                        )
                    else:
                        err_msg = (
                            res_exento.get("message")
                            or res_exento.get("exceptionMessage")
                            or res_exento.get("description")
                            or res_exento.get("detail")
                            or f"Defontana rechazó la creación: {res_exento}"
                        )
                        if _is_address_error(err_msg) and order.direccion:
                            self.update_client(order.cliente, order.direccion, client_data=client_data)
                            res_exento = self.save_order(body_exento)
                            if res_exento.get("success", False) or res_exento.get("isSuccess", False):
                                new_folio = res_exento.get("folio") or res_exento.get("number")
                                if new_folio:
                                    order.folio_defontana = int(new_folio)
                                err_msg = None
                        if err_msg:
                            errors.append(f"Factura 34: {err_msg}")
                            sync_ok = False
                except Exception as exc:
                    err_msg = _extract_defontana_error(exc)
                    if _is_address_error(err_msg) and order.direccion:
                        try:
                            self.update_client(order.cliente, order.direccion, client_data=client_data)
                            res_exento = self.save_order(body_exento)
                            if res_exento.get("success", False) or res_exento.get("isSuccess", False):
                                new_folio = res_exento.get("folio") or res_exento.get("number")
                                if new_folio:
                                    order.folio_defontana = int(new_folio)
                                err_msg = None
                        except Exception as retry_exc:
                            err_msg = _extract_defontana_error(retry_exc)
                    if err_msg:
                        errors.append(f"Factura 34: {err_msg}")
                        sync_ok = False

        # Actualizar estado del pedido
        primary_folio = order.folio_defontana_afecto or order.folio_defontana
        if sync_ok and not errors:
            order.defontana_sincronizado = True
            order.defontana_error = None
            if auto_commit:
                session.commit()
            return primary_folio, None
        else:
            combined_err = " | ".join(errors)
            order.defontana_sincronizado = False
            order.defontana_error = combined_err
            if auto_commit:
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

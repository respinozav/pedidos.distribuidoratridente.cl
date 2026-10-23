"""Servicio de Pedidos por Voz con IA para Distribuidora Tridente.

Flujo:
1. Transcripción de audio (o recepción de texto dictado por Web Speech API).
2. Interpretación semántica con Gemini (cliente, dirección, productos, formatos, cantidades).
3. Resolución contra base de datos (clientes, alias, productos, empaques, candidatos si hay ambigüedad).
4. Verificaciones de reglas de negocio:
   - Alerta si hay múltiples coincidencias (nunca elegir solo).
   - Alerta de stock insuficiente.
   - Alerta de posible pedido duplicado del mismo cliente en el mismo día.
5. Almacenamiento de borrador en `pedidos_voz`.
6. Confirmación humana -> creación de Pedido oficial con origen='voz' y sincronización Defontana.
7. Métricas y estadísticas para el Dashboard de Operación.
"""

import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime, date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, UploadFile, status
from google import genai
from google.genai import types
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.entities import (
    Cliente,
    Direccion,
    Estado,
    Pedido,
    PedidoVoz,
    Producto,
    Usuario,
)
from app.schemas.dto import OrderCreate, OrderLineInput
from app.services.ordering import OrderService
from app.services.pricing import customer_product_box_price, customer_product_price

logger = logging.getLogger(__name__)
settings = get_settings()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "pedidos_voz")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_gemini_client() -> genai.Client:
    api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY no está configurada para el servicio de pedidos por voz",
        )
    return genai.Client(api_key=api_key)


def transcribir_audio_archivo(file_bytes: bytes, mime_type: str) -> str:
    """Transcribe un archivo de audio (WhatsApp, nota de voz, micrófono) usando Gemini."""
    client = _get_gemini_client()
    model_name = settings.gemini_model or "gemini-2.5-flash"

    prompt = (
        "Eres el transcriptor del sistema de pedidos de Distribuidora Tridente en Coquimbo, Chile. "
        "Transcribe de forma exacta, palabra por palabra, lo que dice la persona en español chileno. "
        "Conserva nombres de marcas, clientes, productos, cantidades y términos como 'caja', 'display', 'unidad', 'cajetilla', 'tira'. "
        "Devuelve ÚNICAMENTE el texto transcrito sin explicaciones ni saludos."
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.error(f"Error al transcribir audio con Gemini: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo transcribir el audio: {str(e)}",
        )


import time


def _interpretar_texto_con_gemini(transcripcion: str) -> dict[str, Any]:
    """Extrae entidades estructuradas (cliente, dirección, productos) del texto transcrito con reintento y fallback."""
    client = _get_gemini_client()
    candidate_models = [settings.gemini_model, "gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"]
    # Eliminar duplicados preservando orden
    models_to_try = [m for i, m in enumerate(candidate_models) if m and m not in candidate_models[:i]]

    system_prompt = (
        "Eres un analizador semántico de pedidos para Distribuidora Tridente (mayorista de confites, snacks, tabaco y abarrotes en Coquimbo, Chile).\n"
        "Tu tarea es analizar el dictado del usuario y extraer los datos en formato JSON estricto.\n"
        "Reglas:\n"
        "1. Identifica el nombre o alias del cliente ('cliente_nombre'). Si no lo menciona, null.\n"
        "2. Identifica la dirección o indicación de despacho ('direccion_texto', ej: 'dirección principal', 'local centro').\n"
        "3. Para cada ítem mencionado, extrae:\n"
        "   - 'termino_producto': nombre, apodo o marca del producto (ej: 'Pall Mall Azul 20 XL', 'Bristol rojo', 'Alfajor Classic', 'Bon o Bon blanco', 'Chocman').\n"
        "   - 'cantidad': número entero (si dice 'un par' -> 2, 'una' -> 1, 'media' -> 1 pero marca ambigua).\n"
        "   - 'formato': 'caja', 'display' o 'unidad'. (si no especifica, 'unidad').\n"
        "   - 'es_ambiguo': boolean (true si la cantidad o el producto suena incierto, ej: 'un par', 'media caja', o si hay audio cortado).\n"
        "   - 'texto_original': fragmento textual del ítem.\n"
        "4. Si el dictado parece ruido o no contiene ningún producto ni cliente, 'es_ruido': true, con 'mensaje_ruido': 'Audio no reconocible o sin datos de pedido. Por favor repite el dictado.'\n"
        "Responde SOLO con el JSON válido que cumpla este esquema sin bloques markdown:"
    )

    prompt = (
        f"Dictado a analizar:\n\"\"\"{transcripcion}\"\"\"\n\n"
        "Entrega el JSON con la estructura:\n"
        "{\n"
        "  \"cliente_nombre\": string | null,\n"
        "  \"direccion_texto\": string | null,\n"
        "  \"es_ruido\": boolean,\n"
        "  \"mensaje_ruido\": string | null,\n"
        "  \"items\": [\n"
        "    {\n"
        "      \"termino_producto\": string,\n"
        "      \"cantidad\": number,\n"
        "      \"formato\": \"caja\" | \"display\" | \"unidad\",\n"
        "      \"es_ambiguo\": boolean,\n"
        "      \"texto_original\": string\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    last_error = None
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                data = json.loads(response.text or "{}")
                return data
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                logger.warning(f"Error interpretando pedido con modelo {model_name} (intento {attempt+1}): {e}")
                if "503" in err_str or "429" in err_str or "unavailable" in err_str or "resource_exhausted" in err_str:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                break  # Si es otro error, probar siguiente modelo

    logger.error(f"Falla total al interpretar pedido con Gemini tras reintentos: {last_error}")
    return {
        "cliente_nombre": None,
        "direccion_texto": None,
        "es_ruido": False,
        "items": [],
        "error": str(last_error),
    }


def _buscar_clientes_db(db: Session, cliente_busqueda: str | None) -> tuple[Cliente | None, list[dict[str, Any]]]:
    """Busca cliente por coincidencia exacta o parecida en alias, razón social y RUT."""
    if not cliente_busqueda or not cliente_busqueda.strip():
        return None, []

    termino = cliente_busqueda.strip()
    words = [w for w in re.split(r"\s+", termino) if len(w) >= 3]

    # 1. Match exacto o directo por alias, nombre o RUT
    exactos = db.scalars(
        select(Cliente).where(
            Cliente.activo.is_(True),
            or_(
                func.lower(Cliente.alias) == termino.lower(),
                func.lower(Cliente.nombre) == termino.lower(),
                func.lower(Cliente.rut) == termino.lower(),
            ),
        )
    ).all()

    if len(exactos) == 1:
        return exactos[0], []

    # 2. Match parcial / ILIKE
    condiciones = [
        Cliente.alias.ilike(f"%{termino}%"),
        Cliente.nombre.ilike(f"%{termino}%"),
    ]
    for w in words:
        condiciones.append(Cliente.alias.ilike(f"%{w}%"))
        condiciones.append(Cliente.nombre.ilike(f"%{w}%"))

    candidatos = db.scalars(
        select(Cliente)
        .options(selectinload(Cliente.direcciones))
        .where(Cliente.activo.is_(True), or_(*condiciones))
        .limit(6)
    ).all()

    if len(candidatos) == 1:
        return candidatos[0], []

    candidatos_data = [
        {
            "id": str(c.id),
            "rut": c.rut,
            "nombre": c.nombre,
            "alias": c.alias,
            "direccion": c.direcciones[0].direccion if c.direcciones else None,
        }
        for c in candidatos
    ]

    return None, candidatos_data


def _buscar_productos_db(
    db: Session,
    termino: str,
    cliente: Cliente | None = None,
) -> tuple[Producto | None, list[dict[str, Any]]]:
    """Busca productos por código, nombre o marcas/apodos clave."""
    clean_term = termino.strip()
    if not clean_term:
        return None, []

    # 1. Búsqueda por código exacto o nombre exacto
    exactos = db.scalars(
        select(Producto).where(
            Producto.activo.is_(True),
            or_(
                func.lower(Producto.codigo) == clean_term.lower(),
                func.lower(Producto.nombre) == clean_term.lower(),
            ),
        )
    ).all()

    if len(exactos) == 1:
        return exactos[0], []

    # 2. Búsqueda con ILIKE separando palabras
    words = [w for w in re.split(r"[\s,]+", clean_term) if len(w) >= 2]
    words_filtered = [w for w in words if w.lower() not in {"de", "con", "el", "la", "los", "las", "un", "una", "dos", "tres", "cuatro"}]

    condiciones = [Producto.nombre.ilike(f"%{clean_term}%")]
    for w in words_filtered:
        condiciones.append(Producto.nombre.ilike(f"%{w}%"))
        condiciones.append(Producto.codigo.ilike(f"%{w}%"))

    # Casos especiales de apodos comerciales
    if "bristol rojo" in clean_term.lower():
        condiciones.append(Producto.nombre.ilike("%bristol%red%"))
        condiciones.append(Producto.nombre.ilike("%bristol%rojo%"))
    elif "lucky azul" in clean_term.lower():
        condiciones.append(Producto.nombre.ilike("%lucky%blue%"))
        condiciones.append(Producto.nombre.ilike("%lucky%azul%"))

    candidatos = db.scalars(
        select(Producto)
        .where(Producto.activo.is_(True), or_(*condiciones))
        .limit(10)
    ).all()

    if len(candidatos) == 1:
        return candidatos[0], []

    candidatos_list = []
    for p in candidatos:
        p_u = customer_product_price(p, cliente) if cliente else p.precio
        p_c = customer_product_box_price(p, cliente) if cliente else (p.precio_caja or p.precio)
        candidatos_list.append(
            {
                "id": str(p.id),
                "codigo": p.codigo,
                "nombre": p.nombre,
                "stock": p.cantidad,
                "precio_unitario": float(p_u),
                "precio_caja": float(p_c) if p_c else None,
                "cantidad_caja": p.cantidad_caja,
            }
        )

    return None, candidatos_list


def interpretar_pedido_dictado(
    db: Session,
    usuario_id: uuid.UUID,
    transcripcion: str,
    audio_url: str | None = None,
) -> dict[str, Any]:
    """Flujo completo de interpretación semántica, matching en DB y validaciones."""
    transcripcion_limpia = transcripcion.strip()
    if not transcripcion_limpia:
        raise HTTPException(status_code=400, detail="La transcripción está vacía")

    # 1. Extracción con Gemini
    extraccion = _interpretar_texto_con_gemini(transcripcion_limpia)

    if extraccion.get("es_ruido"):
        return {
            "estado": "RUIDO",
            "mensaje": extraccion.get("mensaje_ruido") or "Audio no reconocible o con mucho ruido. Por favor repita el dictado con mayor claridad.",
            "transcripcion": transcripcion_limpia,
            "borrador_id": None,
        }

    # 2. Identificar cliente
    cliente_encontrado, candidatos_cliente = _buscar_clientes_db(db, extraccion.get("cliente_nombre"))

    direcciones_list: list[dict[str, Any]] = []
    direccion_seleccionada: Direccion | None = None

    if cliente_encontrado:
        direcciones_db = db.scalars(
            select(Direccion).where(Direccion.cliente_id == cliente_encontrado.id, Direccion.activo.is_(True))
        ).all()
        direcciones_list = [
            {
                "id": str(d.id),
                "direccion": d.direccion,
                "comuna": d.comuna,
                "principal": d.principal,
            }
            for d in direcciones_db
        ]
        direccion_seleccionada = next((d for d in direcciones_db if d.principal), None)
        if not direccion_seleccionada and direcciones_db:
            direccion_seleccionada = direcciones_db[0]

    # 3. Detectar posible pedido duplicado del mismo cliente en el mismo día
    alerta_duplicado = None
    if cliente_encontrado:
        hoy_inicio = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        pedido_existente = db.scalar(
            select(Pedido)
            .where(
                Pedido.cliente_id == cliente_encontrado.id,
                Pedido.created_at >= hoy_inicio,
            )
            .order_by(desc(Pedido.created_at))
        )
        if pedido_existente:
            alerta_duplicado = {
                "pedido_id": str(pedido_existente.id),
                "folio_defontana": pedido_existente.folio_defontana,
                "total": float(pedido_existente.total),
                "hora": pedido_existente.created_at.strftime("%H:%M"),
                "mensaje": f"Atención: Este cliente ya tiene un pedido hoy a las {pedido_existente.created_at.strftime('%H:%M')} por ${int(pedido_existente.total):,}. ¿Desea crear otro?".replace(",", "."),
            }

    # 4. Procesar líneas de productos
    lineas_interpretadas: list[dict[str, Any]] = []
    total_estimado = Decimal("0.00")

    for item_dict in extraccion.get("items", []):
        termino = item_dict.get("termino_producto", "").strip()
        cantidad = int(item_dict.get("cantidad", 1))
        if cantidad <= 0:
            cantidad = 1
        formato = (item_dict.get("formato") or "unidad").lower()
        if formato not in {"caja", "display", "unidad"}:
            formato = "unidad"

        prod_match, candidatos_prod = _buscar_productos_db(db, termino, cliente=cliente_encontrado)

        linea: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "texto_original": item_dict.get("texto_original") or termino,
            "termino_busqueda": termino,
            "cantidad": cantidad,
            "formato": formato,
            "es_ambiguo": bool(item_dict.get("es_ambiguo")),
            "producto_id": None,
            "codigo": None,
            "nombre": None,
            "precio_unitario": 0.0,
            "subtotal": 0.0,
            "alerta_stock": False,
            "stock_disponible": 0,
            "candidatos": candidatos_prod,
            "resuelto": False,
        }

        if prod_match:
            linea["producto_id"] = str(prod_match.id)
            linea["codigo"] = prod_match.codigo
            linea["nombre"] = prod_match.nombre
            linea["stock_disponible"] = prod_match.cantidad
            linea["resuelto"] = True

            if formato == "caja":
                p_c = customer_product_box_price(prod_match, cliente_encontrado)
                if p_c is not None:
                    precio = p_c
                    unidades_descontar = cantidad * (prod_match.cantidad_caja or 1)
                else:
                    precio = customer_product_price(prod_match, cliente_encontrado)
                    linea["formato"] = "unidad"
                    unidades_descontar = cantidad
            else:
                precio = customer_product_price(prod_match, cliente_encontrado)
                unidades_descontar = cantidad

            subtotal_linea = precio * cantidad
            linea["precio_unitario"] = float(precio)
            linea["subtotal"] = float(subtotal_linea)
            total_estimado += subtotal_linea

            if prod_match.cantidad < unidades_descontar:
                linea["alerta_stock"] = True
                linea["mensaje_stock"] = (
                    f"Stock insuficiente: se requieren {unidades_descontar} unidades y hay {prod_match.cantidad} disponibles."
                )

        lineas_interpretadas.append(linea)

    # 5. Crear el registro en `pedidos_voz` como BORRADOR
    pedido_voz = PedidoVoz(
        usuario_id=usuario_id,
        cliente_id=cliente_encontrado.id if cliente_encontrado else None,
        direccion_id=direccion_seleccionada.id if direccion_seleccionada else None,
        transcripcion=transcripcion_limpia,
        audio_url=audio_url,
        estado="BORRADOR",
        lineas_interpretadas=lineas_interpretadas,
        total_estimado=total_estimado,
        lineas_editadas_count=0,
    )
    db.add(pedido_voz)
    db.commit()
    db.refresh(pedido_voz)

    return {
        "borrador_id": str(pedido_voz.id),
        "estado": pedido_voz.estado,
        "transcripcion": transcripcion_limpia,
        "audio_url": audio_url,
        "cliente": {
            "id": str(cliente_encontrado.id) if cliente_encontrado else None,
            "rut": cliente_encontrado.rut if cliente_encontrado else None,
            "nombre": cliente_encontrado.nombre if cliente_encontrado else None,
            "alias": cliente_encontrado.alias if cliente_encontrado else None,
        } if cliente_encontrado else None,
        "candidatos_cliente": candidatos_cliente,
        "direcciones": direcciones_list,
        "direccion_seleccionada_id": str(direccion_seleccionada.id) if direccion_seleccionada else None,
        "alerta_duplicado": alerta_duplicado,
        "lineas": lineas_interpretadas,
        "total_estimado": float(total_estimado),
        "created_at": pedido_voz.created_at.isoformat(),
    }


def confirmar_pedido_voz(
    db: Session,
    pedido_voz_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cliente_id: uuid.UUID,
    direccion_id: uuid.UUID,
    lineas: list[dict[str, Any]],
    notas: str | None = None,
) -> dict[str, Any]:
    """Convierte el borrador en un Pedido real en BD, descuenta stock y sincroniza Defontana."""
    pv = db.get(PedidoVoz, pedido_voz_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Borrador de pedido por voz no encontrado")

    if pv.estado != "BORRADOR":
        raise HTTPException(
            status_code=400,
            detail=f"Este pedido por voz ya se encuentra en estado '{pv.estado}'.",
        )

    cliente = db.get(Cliente, cliente_id)
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=422, detail="Cliente inválido o inactivo")

    direccion = db.get(Direccion, direccion_id)
    if not direccion or direccion.cliente_id != cliente_id or not direccion.activo:
        raise HTTPException(status_code=422, detail="Dirección de entrega inválida o inactiva")

    if not lineas:
        raise HTTPException(status_code=422, detail="Debe ingresar al menos una línea de producto")

    lineas_originales = pv.lineas_interpretadas or []
    count_editadas = abs(len(lineas) - len(lineas_originales))
    for idx, nueva in enumerate(lineas):
        if idx < len(lineas_originales):
            orig = lineas_originales[idx]
            if (
                str(nueva.get("producto_id")) != str(orig.get("producto_id"))
                or int(nueva.get("cantidad", 1)) != int(orig.get("cantidad", 1))
                or str(nueva.get("formato", "unidad")) != str(orig.get("formato", "unidad"))
            ):
                count_editadas += 1

    order_create_lines: list[OrderLineInput] = []
    for l in lineas:
        p_id_str = l.get("producto_id")
        if not p_id_str:
            raise HTTPException(
                status_code=422,
                detail=f"Hay líneas sin producto asignado: '{l.get('texto_original', '')}'",
            )
        order_create_lines.append(
            OrderLineInput(
                producto_id=uuid.UUID(str(p_id_str)),
                cantidad=int(l.get("cantidad", 1)),
                tipo_empaque=l.get("formato", "unidad"),
            )
        )

    payload = OrderCreate(
        direccion_id=direccion_id,
        productos=order_create_lines,
    )

    order_service = OrderService(db)
    nuevo_pedido = order_service.create(
        customer_id=cliente_id,
        payload=payload,
        vendedor_id=usuario_id,
        origen="voz",
    )

    pv.cliente_id = cliente_id
    pv.direccion_id = direccion_id
    pv.pedido_id = nuevo_pedido.id
    pv.estado = "CONFIRMADO"
    pv.lineas_editadas_count = count_editadas
    pv.total_estimado = nuevo_pedido.total
    pv.notas = notas
    db.commit()

    return {
        "ok": True,
        "pedido_id": str(nuevo_pedido.id),
        "pedido_voz_id": str(pv.id),
        "total": float(nuevo_pedido.total),
        "estado": nuevo_pedido.estado.nombre if nuevo_pedido.estado else "Pedido",
        "origen": nuevo_pedido.origen,
        "lineas_editadas": count_editadas,
        "mensaje": "Pedido por voz confirmado y creado exitosamente.",
    }


def descartar_pedido_voz(db: Session, pedido_voz_id: uuid.UUID) -> dict[str, Any]:
    """Marca un borrador de pedido por voz como descartado."""
    pv = db.get(PedidoVoz, pedido_voz_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Borrador de pedido por voz no encontrado")

    if pv.estado != "BORRADOR":
        raise HTTPException(status_code=400, detail=f"No se puede descartar un pedido en estado '{pv.estado}'")

    pv.estado = "DESCARTADO"
    db.commit()
    return {"ok": True, "mensaje": "Pedido descartado correctamente"}


def listar_pedidos_voz(
    db: Session,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    cliente_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    estado: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista pedidos por voz con filtros y datos completos para la vista de Operación."""
    query = select(PedidoVoz).options(
        selectinload(PedidoVoz.usuario),
        selectinload(PedidoVoz.cliente),
        selectinload(PedidoVoz.pedido),
    )

    if fecha_desde:
        query = query.where(PedidoVoz.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.where(PedidoVoz.created_at <= fecha_hasta)
    if cliente_id:
        query = query.where(PedidoVoz.cliente_id == cliente_id)
    if usuario_id:
        query = query.where(PedidoVoz.usuario_id == usuario_id)
    if estado:
        query = query.where(PedidoVoz.estado == estado.upper())

    total_count = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(desc(PedidoVoz.created_at)).offset(offset).limit(limit)).all()

    resultados = []
    for pv in items:
        resultados.append(
            {
                "id": str(pv.id),
                "created_at": pv.created_at.isoformat(),
                "usuario_id": str(pv.usuario_id),
                "dictado_por": pv.usuario.nombre if pv.usuario else "Desconocido",
                "cliente_id": str(pv.cliente_id) if pv.cliente_id else None,
                "cliente_nombre": pv.cliente.nombre if pv.cliente else (pv.cliente.alias if pv.cliente else "Sin identificar"),
                "cliente_alias": pv.cliente.alias if pv.cliente else None,
                "total": float(pv.total_estimado),
                "estado": pv.estado,
                "lineas_editadas_count": pv.lineas_editadas_count,
                "audio_url": pv.audio_url,
                "transcripcion": pv.transcripcion,
                "pedido_id": str(pv.pedido_id) if pv.pedido_id else None,
                "lineas": pv.lineas_interpretadas or [],
            }
        )

    return {"total": total_count, "items": resultados}


def obtener_metricas_dashboard_voz(
    db: Session,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> dict[str, Any]:
    """Calcula las métricas de pedidos por voz para el Dashboard."""
    cond_pv = []
    cond_pedidos = []

    if fecha_desde:
        cond_pv.append(PedidoVoz.created_at >= fecha_desde)
        cond_pedidos.append(Pedido.created_at >= fecha_desde)
    if fecha_hasta:
        cond_pv.append(PedidoVoz.created_at <= fecha_hasta)
        cond_pedidos.append(Pedido.created_at <= fecha_hasta)

    q_pv = select(PedidoVoz.estado, func.count(PedidoVoz.id), func.sum(PedidoVoz.total_estimado))
    if cond_pv:
        q_pv = q_pv.where(*cond_pv)
    q_pv = q_pv.group_by(PedidoVoz.estado)
    estados_data = db.execute(q_pv).all()

    dictados_total = 0
    confirmados = 0
    descartados = 0
    borradores = 0
    monto_confirmado_voz = Decimal("0.00")

    for est, cnt, sm in estados_data:
        dictados_total += cnt
        if est == "CONFIRMADO":
            confirmados = cnt
            monto_confirmado_voz = Decimal(str(sm or 0))
        elif est == "DESCARTADO":
            descartados = cnt
        elif est == "BORRADOR":
            borradores = cnt

    q_tot = select(func.sum(Pedido.total))
    if cond_pedidos:
        q_tot = q_tot.where(*cond_pedidos)
    total_ventas_periodo = db.scalar(q_tot) or Decimal("0.00")
    total_ventas_periodo = Decimal(str(total_ventas_periodo))

    porcentaje_voz = 0.0
    if total_ventas_periodo > 0 and monto_confirmado_voz > 0:
        porcentaje_voz = round(float((monto_confirmado_voz / total_ventas_periodo) * 100), 2)

    borradores_pendientes = db.scalars(
        select(PedidoVoz)
        .options(selectinload(PedidoVoz.usuario), selectinload(PedidoVoz.cliente))
        .where(PedidoVoz.estado == "BORRADOR")
        .order_by(desc(PedidoVoz.created_at))
        .limit(5)
    ).all()

    borradores_list = [
        {
            "id": str(b.id),
            "created_at": b.created_at.isoformat(),
            "dictado_por": b.usuario.nombre if b.usuario else "Usuario",
            "cliente_nombre": b.cliente.nombre if b.cliente else "Por identificar",
            "total_estimado": float(b.total_estimado),
            "transcripcion_corta": (b.transcripcion[:80] + "...") if len(b.transcripcion) > 80 else b.transcripcion,
        }
        for b in borradores_pendientes
    ]

    return {
        "dictados_total": dictados_total,
        "confirmados": confirmados,
        "descartados": descartados,
        "borradores_pendientes_count": borradores,
        "monto_confirmado_voz": float(monto_confirmado_voz),
        "total_ventas_periodo": float(total_ventas_periodo),
        "porcentaje_ventas_voz": porcentaje_voz,
        "borradores_pendientes": borradores_list,
    }

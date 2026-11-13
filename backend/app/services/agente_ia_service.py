import json
import logging
import re
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.entities import IAChat, IAMensaje, Usuario
from app.services.postgrest_service import PostgrestService

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_INSTRUCTION = """
Eres el **Agente Tridente IA**, el asistente inteligente de analítica comercial, rotación de inventario y abastecimiento de Distribuidora Tridente.
Tu objetivo es asesorar a los administradores, dueños y ejecutivos comerciales de la empresa.

AUDIENCIA Y TONO:
- Tu interlocutor es un usuario comercial/administrativo, **NO ES INFORMÁTICO NI PROGRAMADOR**.
- **ESTÁ ESTRICTAMENTE PROHIBIDO responder con objetos JSON, código fuente o estructuras de programación en el texto que lee el usuario.**
- NUNCA uses bloques de código con sintaxis técnica como `{"clave": "valor"}` o `[{"id": 1}]`.
- NUNCA menciones nombres de tecnologías internas como PostgreSQL, PostgREST, SQL o bases de datos al responder. Para el usuario simplemente estás consultando el catálogo y las ventas de Distribuidora Tridente.
- Comunícate siempre en un tono profesional, claro, ejecutivo y cordial en español (Chile).

REGLA DE ORO: SIEMPRE RESPONDE CON TABLAS MARKDOWN
1. Toda lista de productos, stock, compras, pedidos, clientes, precios o métricas DEBE presentarse obligatoriamente en formato de **TABLA MARKDOWN** (`| Encabezado | ... |`).
   Ejemplo de tabla obligatoria:
   | Código | Producto | Stock Actual | Precio | Estado |
   | :--- | :--- | :---: | :---: | :--- |
   | PROD-01 | Arroz Extra 1kg | 24 un. | $1.290 | Disponible ✅ |
   | PROD-05 | Aceite Vegetal 900ml | 4 un. | $2.190 | Stock Crítico ⚠️ |

2. Formato de datos en las tablas:
   - Precios: siempre con formato de moneda en pesos chilenos (ej: `$1.500`, `$24.990`).
   - Cantidades: siempre con unidad de medida clara (ej: `15 un.`, `8 cajas`, `0 un. (Agotado 🚨)`).
   - Fechas: formato legible día/mes/año (ej: `14/10/2026`).

3. Complementa la tabla con un análisis ejecutivo:
   - Inicia con una breve introducción directa al grano.
   - Presenta la tabla con los datos solicitados.
   - Concluye con recomendaciones comerciales prácticas (ej: sugerencias de compra, clientes que han dejado de comprar, etc.).

HERRAMIENTAS EN TIEMPO REAL:
Tienes herramientas disponibles para consultar el catálogo de productos y ventas en tiempo real:
1. `consultar_productos`: busca productos por nombre/código, stock o estado.
2. `consultar_pedidos_recientes`: consulta pedidos y compras de clientes en un rango de días.
3. `consultar_metricas_generales`: obtiene métricas consolidadas (top más vendidos, total facturado, stock crítico).
DEBES utilizarlas para responder con datos reales y actualizados. No inventes números ni productos.

GRÁFICOS Y PREDICCIONES INTERACTIVAS (OPCIONAL):
Si el usuario te pide expresamente un gráfico o una predicción visual, presenta primero tu explicación y tu TABLA con los datos para el usuario, y luego, al final absoluto de tu mensaje, incluye el bloque técnico de datos para el motor gráfico con uno de estos formatos:

```json
{
  "type": "chart",
  "chartType": "bar",
  "title": "Top 5 Productos más Vendidos",
  "description": "Comparativa de unidades vendidas",
  "data": {
    "labels": ["Prod A", "Prod B"],
    "datasets": [
      {
        "label": "Unidades",
        "data": [120, 85],
        "backgroundColor": ["#0ea5e9", "#10b981"]
      }
    ]
  }
}
```

o para predicción:
```json
{
  "type": "prediction",
  "title": "Sugerencias de Reabastecimiento Crítico",
  "items": [
    {
      "codigo": "PROD-01",
      "nombre": "Nombre del Producto",
      "stock_actual": 4,
      "ventas_periodo": 45,
      "dias_cobertura_estimados": 3,
      "sugerencia_compra": 50
    }
  ]
}
```
Nota: El sistema extraerá automáticamente este bloque para dibujar el gráfico y lo ocultará del texto del mensaje para que el usuario nunca vea código JSON. Por eso es vital que antes del bloque hayas incluido la tabla con los datos para que el usuario pueda leerla directamente.
"""

GEMINI_TOOLS_DECLARATION = [
    {
        "functionDeclarations": [
            {
                "name": "consultar_productos",
                "description": "Consulta productos en el catálogo de Distribuidora Tridente por término de búsqueda, stock o estado activo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "termino_busqueda": {
                            "type": "STRING",
                            "description": "Palabra clave para buscar en nombre o código del producto.",
                        },
                        "solo_activos": {
                            "type": "BOOLEAN",
                            "description": "Si es true, sólo retorna productos activos y no eliminados.",
                        },
                        "ordenar_por_stock_asc": {
                            "type": "BOOLEAN",
                            "description": "Si es true, ordena primero los productos con menos stock.",
                        },
                        "limite": {
                            "type": "INTEGER",
                            "description": "Número máximo de productos a retornar (por defecto 35).",
                        },
                    },
                },
            },
            {
                "name": "consultar_pedidos_recientes",
                "description": "Consulta los pedidos recientes y sus detalles de venta en tiempo real.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "dias_historial": {
                            "type": "INTEGER",
                            "description": "Cantidad de días hacia atrás a consultar (ej. 7, 30, 60).",
                        },
                        "estado_filtro": {
                            "type": "STRING",
                            "description": "Filtrar por estado del pedido (opcional).",
                        },
                        "limite": {
                            "type": "INTEGER",
                            "description": "Número máximo de pedidos a retornar.",
                        },
                    },
                },
            },
            {
                "name": "consultar_metricas_generales",
                "description": "Obtiene métricas clave: total pedidos, facturación total, ticket promedio, top 10 productos más vendidos y productos con stock crítico.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "dias": {
                            "type": "INTEGER",
                            "description": "Días del periodo para el análisis (por defecto 30).",
                        },
                    },
                },
            },
        ]
    }
]


def _json_a_tabla_markdown(datos: Any) -> str:
    """Convierte listas de diccionarios o estructuras JSON a una tabla Markdown legible."""
    if isinstance(datos, dict):
        for key in ("productos", "pedidos", "items", "datos", "data", "ventas", "ranking"):
            if key in datos and isinstance(datos[key], list) and datos[key]:
                datos = datos[key]
                break
        else:
            filas = [
                "| Parámetro | Valor |",
                "| :--- | :--- |",
            ]
            for k, v in datos.items():
                k_bonito = str(k).replace("_", " ").title()
                filas.append(f"| {k_bonito} | {v} |")
            return "\n".join(filas)

    if isinstance(datos, list) and datos:
        if all(isinstance(elem, dict) for elem in datos):
            columnas = []
            for elem in datos:
                for k in elem.keys():
                    if k not in columnas:
                        columnas.append(k)
            if not columnas:
                return ""
            encabezados = [c.replace("_", " ").title() for c in columnas]
            header_row = "| " + " | ".join(encabezados) + " |"
            sep_row = "| " + " | ".join([":---"] * len(columnas)) + " |"
            filas = [header_row, sep_row]
            for elem in datos:
                valores = [str(elem.get(c, "-")).replace("\n", " ") for c in columnas]
                filas.append("| " + " | ".join(valores) + " |")
            return "\n".join(filas)
    return ""


class GeminiKeyRotator:
    """
    Gestiona un pool de API Keys / Tokens para el Agente IA de Gemini con:
    - Rotación Round-Robin entre múltiples keys para balancear el consumo de tokens y cuotas.
    - Fallback reactivo automático si una key arroja HTTP 401 (deshabilitada/eliminada), 403 o 429 (sin tokens/cuota).
    - Memoria temporal de keys fallidas para priorizar las llaves operativas.
    """
    _current_index: int = 0
    _failed_keys: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_keys(cls) -> list[str]:
        cfg = get_settings()
        return cfg.get_gemini_api_keys()

    @classmethod
    def get_ordered_pool(cls) -> list[str]:
        all_keys = cls.get_keys()
        if not all_keys:
            return []

        now = time.time()
        # Limpiar keys que fallaron hace más de 5 minutos (300s)
        cls._failed_keys = {k: v for k, v in cls._failed_keys.items() if now - v.get("timestamp", 0) < 300}

        healthy_keys = [k for k in all_keys if k not in cls._failed_keys]
        failed_keys = [k for k in all_keys if k in cls._failed_keys]

        if healthy_keys:
            idx = cls._current_index % len(healthy_keys)
            ordered_healthy = healthy_keys[idx:] + healthy_keys[:idx]
            return ordered_healthy + failed_keys

        idx = cls._current_index % len(all_keys)
        return all_keys[idx:] + all_keys[:idx]

    @classmethod
    def advance_index(cls) -> None:
        keys = cls.get_keys()
        if keys:
            cls._current_index = (cls._current_index + 1) % len(keys)

    @classmethod
    def mark_key_failed(cls, key: str, reason: str = "") -> None:
        now = time.time()
        cls._failed_keys[key] = {"timestamp": now, "reason": reason}
        masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
        logger.warning(
            "Gemini API Key %s marcada con fallo temporal (%s). Rotando a siguiente key del pool...",
            masked,
            reason,
        )
        cls.advance_index()

    @classmethod
    def mark_key_success(cls, key: str) -> None:
        cls._failed_keys.pop(key, None)

    @classmethod
    def get_status_summary(cls) -> dict[str, Any]:
        all_keys = cls.get_keys()
        now = time.time()
        cls._failed_keys = {k: v for k, v in cls._failed_keys.items() if now - v.get("timestamp", 0) < 300}

        detalles = []
        for k in all_keys:
            masked = k[:4] + "..." + k[-4:] if len(k) > 8 else "***"
            is_failed = k in cls._failed_keys
            info_fallo = cls._failed_keys.get(k, {})
            detalles.append({
                "key_prefijo": masked,
                "estado": "fallida_temporal" if is_failed else "activa",
                "motivo_fallo": info_fallo.get("reason"),
                "segundos_desde_fallo": int(now - info_fallo.get("timestamp", 0)) if is_failed else None,
            })
        return {
            "total_keys": len(all_keys),
            "keys_activas": len(all_keys) - len(cls._failed_keys),
            "keys_fallidas": len(cls._failed_keys),
            "detalles": detalles,
        }


class AgenteIAService:
    def __init__(self, db: Session, usuario: Usuario):
        self.db = db
        self.usuario = usuario
        self.postgrest = PostgrestService(db)
        self.api_keys = GeminiKeyRotator.get_keys()
        self.api_key = self.api_keys[0] if self.api_keys else ""

    def ejecutar_herramienta(self, nombre: str, args: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta la función solicitada por Gemini vía PostgREST o fallback local."""
        logger.info("Agente IA ejecutando herramienta '%s' con args %s", nombre, args)
        if nombre == "consultar_productos":
            return {
                "productos": self.postgrest.consultar_productos(
                    termino_busqueda=args.get("termino_busqueda", ""),
                    solo_activos=args.get("solo_activos", True),
                    ordenar_por_stock_asc=args.get("ordenar_por_stock_asc", None),
                    limite=args.get("limite", 35),
                )
            }
        elif nombre == "consultar_pedidos_recientes":
            return {
                "pedidos": self.postgrest.consultar_pedidos_recientes(
                    dias_historial=args.get("dias_historial", 30),
                    estado_filtro=args.get("estado_filtro", None),
                    limite=args.get("limite", 35),
                )
            }
        elif nombre == "consultar_metricas_generales":
            return {
                "metricas": self.postgrest.consultar_metricas_generales(
                    dias=args.get("dias", 30)
                )
            }
        return {"error": f"Herramienta '{nombre}' desconocida."}

    def _extraer_datos_estructurados(self, texto: str) -> tuple[str, dict[str, Any] | None]:
        """
        Extrae datos para gráficos/predicciones y limpia el texto para garantizar
        que NUNCA se muestre código JSON a los usuarios no técnicos.
        Convierte cualquier bloque JSON residual en tablas Markdown legibles.
        """
        datos_estructurados = None
        texto_limpio = texto

        # 1. Buscar bloques de código ```json ... ``` o ``` ... ```
        patron_bloques = r"```(?:json)?\s*([\s\S]*?)\s*```"
        bloques = re.findall(patron_bloques, texto)

        for contenido_bloque in bloques:
            contenido_trim = contenido_bloque.strip()
            # Intentar parsear como JSON si tiene forma de estructura
            if (contenido_trim.startswith("{") and contenido_trim.endswith("}")) or (
                contenido_trim.startswith("[") and contenido_trim.endswith("]")
            ):
                try:
                    parsed = json.loads(contenido_trim)
                    if isinstance(parsed, dict) and parsed.get("type") in ("chart", "prediction"):
                        if not datos_estructurados:
                            datos_estructurados = parsed
                        # Eliminar el bloque de código del texto para no mostrar JSON al usuario
                        texto_limpio = re.sub(
                            r"```(?:json)?\s*" + re.escape(contenido_bloque) + r"\s*```",
                            "",
                            texto_limpio,
                        )
                    else:
                        # Si es un JSON de datos (ej: lista de productos o métricas), convertir a tabla Markdown
                        tabla_md = _json_a_tabla_markdown(parsed)
                        if tabla_md:
                            # Reemplazar el bloque de código técnico por una tabla Markdown elegante
                            texto_limpio = re.sub(
                                r"```(?:json)?\s*" + re.escape(contenido_bloque) + r"\s*```",
                                f"\n\n{tabla_md}\n\n",
                                texto_limpio,
                            )
                        else:
                            texto_limpio = re.sub(
                                r"```(?:json)?\s*" + re.escape(contenido_bloque) + r"\s*```",
                                "",
                                texto_limpio,
                            )
                except Exception:
                    pass

        # 2. Si no se encontró en bloques ``` pero viene un JSON suelto {"type": "chart" | "prediction"}
        if not datos_estructurados:
            match = re.search(r'(\{\s*"type"\s*:\s*"(?:chart|prediction)"[\s\S]*?\})', texto_limpio)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, dict) and parsed.get("type") in ("chart", "prediction"):
                        datos_estructurados = parsed
                        texto_limpio = texto_limpio.replace(match.group(1), "")
                except Exception:
                    pass

        # 3. Limpiar cualquier JSON residual si la IA respondió directamente con JSON sin formato
        texto_limpio_strip = texto_limpio.strip()
        if (texto_limpio_strip.startswith("{") and texto_limpio_strip.endswith("}")) or (
            texto_limpio_strip.startswith("[") and texto_limpio_strip.endswith("]")
        ):
            try:
                parsed_residual = json.loads(texto_limpio_strip)
                tabla_residual = _json_a_tabla_markdown(parsed_residual)
                if tabla_residual:
                    texto_limpio = (
                        "A continuación se detallan los datos consultados en formato de tabla:\n\n"
                        + tabla_residual
                    )
            except Exception:
                pass

        # 4. Asegurarse de que no quede texto vacío si todo era el bloque del gráfico
        texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio).strip()
        if not texto_limpio and datos_estructurados:
            if datos_estructurados.get("type") == "chart":
                texto_limpio = f"A continuación se presenta el gráfico: **{datos_estructurados.get('title', 'Análisis Gráfico')}**."
            elif datos_estructurados.get("type") == "prediction":
                texto_limpio = f"A continuación se presentan las estimaciones: **{datos_estructurados.get('title', 'Sugerencias de Abastecimiento')}**."

        return texto_limpio, datos_estructurados

    def procesar_mensaje(self, chat_id: UUID, mensaje_usuario: str) -> dict[str, Any]:
        """
        Orquesta la conversación con Gemini usando HTTP REST puro vía httpx:
        - Cero dependencias externas incompatibles.
        - Soporta Function Calling nativo con PostgREST.
        - Fallback a modelos alternativos en caso de rate-limit o 503.
        """
        chat = self.db.scalar(
            select(IAChat)
            .options(selectinload(IAChat.mensajes))
            .where(IAChat.id == chat_id, IAChat.usuario_id == self.usuario.id)
        )
        if not chat:
            raise ValueError("Chat no encontrado o no autorizado")

        # Guardar mensaje del usuario
        msg_user = IAMensaje(
            chat_id=chat.id,
            rol="user",
            contenido=mensaje_usuario,
            datos_estructurados=None,
            herramientas_usadas=None,
        )
        self.db.add(msg_user)
        self.db.flush()

        if chat.titulo == "Nueva conversación":
            titulo_auto = mensaje_usuario.strip()[:40]
            if len(mensaje_usuario.strip()) > 40:
                titulo_auto += "..."
            chat.titulo = titulo_auto

        active_keys = GeminiKeyRotator.get_ordered_pool()
        if not active_keys:
            texto_respuesta = (
                "⚠️ **Aviso del Sistema:** No hay claves `GEMINI_API_KEY` o `GEMINI_API_KEYS` configuradas en el servidor. "
                "Por favor, define una o varias claves en el archivo `.env` del backend para activar las respuestas de IA."
            )
            msg_ia = IAMensaje(
                chat_id=chat.id,
                rol="assistant",
                contenido=texto_respuesta,
                datos_estructurados=None,
                herramientas_usadas=None,
            )
            self.db.add(msg_ia)
            chat.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(msg_ia)
            return {
                "id": str(msg_ia.id or uuid4()),
                "chat_id": str(chat.id),
                "rol": "assistant",
                "contenido": msg_ia.contenido,
                "datos_estructurados": None,
                "herramientas_usadas": None,
                "created_at": (msg_ia.created_at or datetime.now()).isoformat(),
            }

        # Armar historial de contents para la API de Gemini (omitiendo mensajes de error del sistema)
        turnos_crudos: list[dict[str, Any]] = []
        for m in chat.mensajes:
            if m.id == msg_user.id:
                continue
            contenido_m = m.contenido.strip() if m.contenido else ""
            if not contenido_m or contenido_m.startswith("⚠️") or "no pudo completar la consulta" in contenido_m:
                continue
            role = "user" if m.rol == "user" else "model"
            turnos_crudos.append({"role": role, "parts": [{"text": contenido_m}]})

        # Sanitizar alternancia user / model para cumplir estrictamente con Gemini API
        contents: list[dict[str, Any]] = []
        for turno in turnos_crudos:
            if not contents:
                if turno["role"] == "user":
                    contents.append(turno)
            else:
                if turno["role"] != contents[-1]["role"]:
                    contents.append(turno)
                else:
                    # Mismo rol consecutivo: concatenar texto para mantener alternancia
                    contents[-1]["parts"][0]["text"] += f"\n\n{turno['parts'][0]['text']}"

        # Agregar el mensaje actual del usuario garantizando alternancia
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"][0]["text"] += f"\n\n{mensaje_usuario}"
        else:
            contents.append({"role": "user", "parts": [{"text": mensaje_usuario}]})

        modelo_env = getattr(settings, "gemini_model", None)
        if modelo_env in ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"):
            modelo_env = "gemini-3.8-flash"

        lista_base = [
            modelo_env if modelo_env else "gemini-3.8-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.6-flash",
            "gemini-flash-lite-latest",
        ]
        # Eliminar duplicados manteniendo orden de prioridad
        modelos_candidatos = list(dict.fromkeys(lista_base))

        herramientas_ejecutadas: list[str] = []
        texto_final = ""
        errores_intentos: list[str] = []

        with httpx.Client(timeout=30.0) as client:
            for current_key in active_keys:
                key_masked = current_key[:4] + "..." + current_key[-4:] if len(current_key) > 8 else "***"
                key_invalid = False

                for modelo in modelos_candidatos:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={current_key}"
                    try:
                        current_contents = [dict(c) for c in contents]
                        payload = {
                            "contents": current_contents,
                            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                            "tools": GEMINI_TOOLS_DECLARATION,
                            "generationConfig": {
                                "temperature": 0.3,
                                "maxOutputTokens": 2048,
                            },
                        }

                        # Bucle de Function Calling (máximo 4 iteraciones)
                        for iteracion in range(4):
                            res = client.post(url, json=payload)
                            if res.status_code != 200:
                                err_info = f"[Key:{key_masked}|{modelo}] HTTP {res.status_code}: {res.text[:120]}"
                                logger.warning("Gemini error: %s", err_info)
                                errores_intentos.append(err_info)

                                if res.status_code in (401, 403):
                                    GeminiKeyRotator.mark_key_failed(current_key, f"HTTP {res.status_code} Auth/Disabled")
                                    key_invalid = True
                                    break
                                elif res.status_code == 429:
                                    GeminiKeyRotator.mark_key_failed(current_key, "HTTP 429 Quota Exceeded")
                                    key_invalid = True
                                    break
                                else:
                                    break

                            res_json = res.json()
                            candidates = res_json.get("candidates", [])
                            if not candidates:
                                err_info = f"[Key:{key_masked}|{modelo}] Sin candidatos en respuesta: {str(res_json)[:100]}"
                                logger.warning(err_info)
                                errores_intentos.append(err_info)
                                break

                            content_candidate = candidates[0].get("content", {})
                            parts = content_candidate.get("parts", [])

                            # Verificar si hay functionCall
                            function_calls = [p.get("functionCall") for p in parts if "functionCall" in p]
                            if not function_calls:
                                # Tenemos respuesta de texto final
                                textos = [p.get("text", "") for p in parts if "text" in p]
                                texto_final = "\n".join(textos).strip()
                                GeminiKeyRotator.mark_key_success(current_key)
                                break

                            # Ejecutar llamadas a herramientas y enviar respuestas a Gemini
                            payload["contents"].append(content_candidate)

                            response_parts = []
                            for fc in function_calls:
                                fn_name = fc.get("name")
                                fn_args = fc.get("args", {})
                                herramientas_ejecutadas.append(fn_name)
                                tool_result = self.ejecutar_herramienta(fn_name, fn_args)
                                response_parts.append(
                                    {
                                        "functionResponse": {
                                            "name": fn_name,
                                            "response": {"result": tool_result},
                                        }
                                    }
                                )

                            payload["contents"].append(
                                {
                                    "role": "user",
                                    "parts": response_parts,
                                }
                            )

                        if texto_final:
                            GeminiKeyRotator.advance_index()
                            break

                        if key_invalid:
                            # Esta llave falló por 401/403/429. Saltar inmediatamente a la siguiente llave
                            break

                    except Exception as ex:
                        err_info = f"[Key:{key_masked}|{modelo}] Excepción {type(ex).__name__}: {str(ex)[:120]}"
                        logger.warning("Fallo llamando a modelo: %s", err_info)
                        errores_intentos.append(err_info)
                        continue

                if texto_final:
                    break

        if not texto_final:
            detalle_fallos = " // ".join(errores_intentos) if errores_intentos else "Sin respuesta de modelos"
            tiene_401 = any("HTTP 401" in err or "deleted or disabled" in err for err in errores_intentos)
            consejo = ""
            if tiene_401:
                consejo = (
                    "\n\n💡 **Causa detectada:** Una o más claves de API configuradas fueron rechazadas por Google "
                    "(cuenta de servicio eliminada o deshabilitada). "
                    "Para solucionarlo, puedes obtener una o varias claves en "
                    "[Google AI Studio](https://aistudio.google.com/app/apikey) (comienzan con `AIzaSy...`) "
                    "y configurarlas separadas por coma en `GEMINI_API_KEY` o `GEMINI_API_KEYS`."
                )

            texto_final = (
                f"El Agente Tridente IA no pudo completar la consulta en este momento.\n\n"
                f"> 🔍 **Diagnóstico de conexión:** `{detalle_fallos}`\n"
                f"{consejo}\n\n"
                f"Por favor verifica la conexión o intenta nuevamente en unos segundos."
            )

        texto_limpio, datos_estructurados = self._extraer_datos_estructurados(texto_final)

        msg_ia = IAMensaje(
            chat_id=chat.id,
            rol="assistant",
            contenido=texto_limpio,
            datos_estructurados=datos_estructurados,
            herramientas_usadas=herramientas_ejecutadas if herramientas_ejecutadas else None,
        )
        self.db.add(msg_ia)
        chat.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(msg_ia)

        return {
            "id": str(msg_ia.id or uuid4()),
            "chat_id": str(chat.id),
            "rol": "assistant",
            "contenido": msg_ia.contenido,
            "datos_estructurados": msg_ia.datos_estructurados,
            "herramientas_usadas": msg_ia.herramientas_usadas,
            "created_at": (msg_ia.created_at or datetime.now()).isoformat(),
        }

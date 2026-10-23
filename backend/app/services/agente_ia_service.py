import json
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.entities import IAChat, IAMensaje, Usuario
from app.services.postgrest_service import PostgrestService

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_INSTRUCTION = """
Eres el Agente Tridente IA, asistente interno de Distribuidora Tridente (mayorista de confites, snacks, tabaco y abarrotes en la Región de Coquimbo). Hablas con el dueño y el equipo de ventas.

Forma de responder:
- Español de Chile, directo y breve. Sin saludos formales ni "Estimado equipo".
- Primera línea = la respuesta con su número (ej.: "Del 1 al 21 de octubre vendimos $69.569.224 en 135 pedidos.").
- Indica siempre el período y si incluye o excluye pedidos cancelados.
- Montos en pesos chilenos con punto de miles ($1.234.567).
- Tablas solo cuando haya 3 o más filas. Máximo 3 recomendaciones, concretas y basadas en los datos.

Datos:
- Usa siempre las herramientas para cifras. Nunca estimes ni inventes montos, stock ni clientes.
- Para ventas, pedidos y clientes, consulta TODOS los pedidos del rango de fechas pedido usando la herramienta `consultar_ventas_periodo` o `consultar_top_clientes`.
- Si no indican fechas, usa el mes en curso y dilo explícitamente.
- Si una herramienta falla o los datos están incompletos, dilo claramente y no entregues cifras parciales como totales.
- Si no tienes un dato, responde "No tengo ese dato en el sistema".
- Para consultar productos con bajo stock, usa `consultar_productos_stock_critico`.

Gráficos:
- Cuando pidan un gráfico, entrega los datos estructurados con valores numéricos limpios (números enteros o decimales puros, sin puntos de miles ni signo $).
- Si solicitan gráfico o visualización, presenta primero tu explicación y tu tabla con los datos para el usuario, y luego, al final absoluto de tu mensaje, incluye el bloque técnico de datos para el motor gráfico con el siguiente formato:

```json
{
  "type": "chart",
  "chartType": "bar",
  "title": "Top Clientes con Mayor Compra",
  "description": "Período consultado",
  "data": {
    "labels": ["Cliente 1", "Cliente 2"],
    "datasets": [
      {
        "label": "Monto Comprado ($)",
        "data": [3624667, 2486101]
      }
    ]
  }
}
```
"""

GEMINI_TOOLS_DECLARATION = [
    {
        "functionDeclarations": [
            {
                "name": "consultar_ventas_periodo",
                "description": "Calcula los totales exactos de ventas, facturación y pedidos en un rango de fechas sobre TODOS los pedidos de la base de datos (sin límites ni recortes). Coincide al 100% con el Dashboard comercial.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fecha_desde": {
                            "type": "STRING",
                            "description": "Fecha inicio del rango en formato YYYY-MM-DD (ej: '2026-10-01'). Si no se indica, usa el inicio del mes actual.",
                        },
                        "fecha_hasta": {
                            "type": "STRING",
                            "description": "Fecha término del rango en formato YYYY-MM-DD (ej: '2026-10-21'). Si no se indica, usa la fecha actual.",
                        },
                        "incluir_cancelados": {
                            "type": "BOOLEAN",
                            "description": "Si es true incluye pedidos cancelados. Por defecto false (excluye cancelados, igual que el Dashboard).",
                        },
                    },
                },
            },
            {
                "name": "consultar_top_clientes",
                "description": "Obtiene el ranking de los clientes con mayores compras en un rango de fechas con valores numéricos limpios listos para graficar y tabular.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fecha_desde": {
                            "type": "STRING",
                            "description": "Fecha inicial YYYY-MM-DD.",
                        },
                        "fecha_hasta": {
                            "type": "STRING",
                            "description": "Fecha final YYYY-MM-DD.",
                        },
                        "limite": {
                            "type": "INTEGER",
                            "description": "Cantidad de clientes en el ranking (por defecto 10).",
                        },
                    },
                },
            },
            {
                "name": "consultar_productos_stock_critico",
                "description": "Consulta productos activos con stock menor o igual al umbral crítico devolviendo la lista completa sin cortes.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "stock_maximo": {
                            "type": "INTEGER",
                            "description": "Cantidad de stock máximo para considerar crítico (por defecto 10).",
                        },
                        "limite": {
                            "type": "INTEGER",
                            "description": "Máximo de productos a listar (por defecto 50).",
                        },
                    },
                },
            },
            {
                "name": "consultar_productos",
                "description": "Busca productos en el catálogo de Distribuidora Tridente por término de búsqueda, stock o estado activo.",
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
                "description": "Consulta los pedidos recientes y sus detalles de venta con filtros de fecha o estado.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fecha_desde": {
                            "type": "STRING",
                            "description": "Fecha inicial YYYY-MM-DD (opcional).",
                        },
                        "fecha_hasta": {
                            "type": "STRING",
                            "description": "Fecha final YYYY-MM-DD (opcional).",
                        },
                        "dias_historial": {
                            "type": "INTEGER",
                            "description": "Cantidad de días hacia atrás si no se especifican fechas (ej. 7, 30).",
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
                "description": "Obtiene métricas consolidadas: total pedidos, facturación total, ticket promedio, top productos y stock crítico.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fecha_desde": {
                            "type": "STRING",
                            "description": "Fecha inicial YYYY-MM-DD (opcional).",
                        },
                        "fecha_hasta": {
                            "type": "STRING",
                            "description": "Fecha final YYYY-MM-DD (opcional).",
                        },
                        "dias": {
                            "type": "INTEGER",
                            "description": "Días del periodo para el análisis si no se indican fechas (por defecto 30).",
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


class AgenteIAService:
    def __init__(self, db: Session, usuario: Usuario):
        self.db = db
        self.usuario = usuario
        self.postgrest = PostgrestService(db)
        self.api_key = settings.gemini_api_key
        self.ultimo_resultado_verificado = False
        self.ultimo_periodo = None
        self.ultima_fuente = None

    def ejecutar_herramienta(self, nombre: str, args: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta la función solicitada por Gemini vía PostgREST o fallback local."""
        logger.info("Agente IA ejecutando herramienta '%s' con args %s", nombre, args)
        if nombre == "consultar_ventas_periodo":
            res = self.postgrest.consultar_ventas_periodo(
                fecha_desde=args.get("fecha_desde"),
                fecha_hasta=args.get("fecha_hasta"),
                incluir_cancelados=args.get("incluir_cancelados", False),
            )
            self.ultimo_resultado_verificado = res.get("verificado", False)
            self.ultimo_periodo = res.get("periodo")
            self.ultima_fuente = res.get("fuente")
            return res
        elif nombre == "consultar_top_clientes":
            res = self.postgrest.consultar_top_clientes(
                fecha_desde=args.get("fecha_desde"),
                fecha_hasta=args.get("fecha_hasta"),
                limite=args.get("limite", 10),
            )
            self.ultimo_resultado_verificado = res.get("verificado", False)
            self.ultimo_periodo = res.get("periodo")
            self.ultima_fuente = "Base de datos Tridente (todos los pedidos)"
            return res
        elif nombre == "consultar_productos_stock_critico":
            res = self.postgrest.consultar_productos_stock_critico(
                stock_maximo=args.get("stock_maximo", 10),
                limite=args.get("limite", 50),
            )
            self.ultimo_resultado_verificado = res.get("verificado", False)
            self.ultimo_periodo = "Inventario actual"
            self.ultima_fuente = res.get("fuente")
            return res
        elif nombre == "consultar_productos":
            return {
                "productos": self.postgrest.consultar_productos(
                    termino_busqueda=args.get("termino_busqueda", ""),
                    solo_activos=args.get("solo_activos", True),
                    ordenar_por_stock_asc=args.get("ordenar_por_stock_asc", None),
                    limite=args.get("limite", 35),
                )
            }
        elif nombre == "consultar_pedidos_recientes":
            res = self.postgrest.consultar_pedidos_recientes(
                fecha_desde=args.get("fecha_desde"),
                fecha_hasta=args.get("fecha_hasta"),
                dias_historial=args.get("dias_historial", 30),
                estado_filtro=args.get("estado_filtro", None),
                limite=args.get("limite", 35),
            )
            self.ultimo_resultado_verificado = res.get("verificado", False)
            self.ultimo_periodo = res.get("periodo")
            self.ultima_fuente = res.get("fuente")
            return res
        elif nombre == "consultar_metricas_generales":
            res = self.postgrest.consultar_metricas_generales(
                fecha_desde=args.get("fecha_desde"),
                fecha_hasta=args.get("fecha_hasta"),
                dias=args.get("dias", 30),
            )
            self.ultimo_resultado_verificado = res.get("verificado", False)
            self.ultimo_periodo = res.get("periodo")
            self.ultima_fuente = res.get("fuente")
            return res
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
            if (contenido_trim.startswith("{") and contenido_trim.endswith("}")) or (
                contenido_trim.startswith("[") and contenido_trim.endswith("]")
            ):
                try:
                    parsed = json.loads(contenido_trim)
                    if isinstance(parsed, dict) and parsed.get("type") in ("chart", "prediction"):
                        if not datos_estructurados:
                            datos_estructurados = parsed
                        texto_limpio = re.sub(
                            r"```(?:json)?\s*" + re.escape(contenido_bloque) + r"\s*```",
                            "",
                            texto_limpio,
                        )
                    else:
                        tabla_md = _json_a_tabla_markdown(parsed)
                        if tabla_md:
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

        # 5. Sanitizar datos numéricos de gráficos (limpiar $, puntos y comas para que Chart.js nunca falle)
        if datos_estructurados and datos_estructurados.get("type") == "chart":
            chart_data = datos_estructurados.get("data", {})
            datasets = chart_data.get("datasets", [])
            for ds in datasets:
                cleaned_numbers = []
                for val in ds.get("data", []):
                    if isinstance(val, (int, float)):
                        cleaned_numbers.append(val)
                    else:
                        s_val = re.sub(r"[$ \s]", "", str(val)).replace(".", "").replace(",", ".")
                        try:
                            cleaned_numbers.append(float(s_val) if "." in s_val else int(s_val))
                        except Exception:
                            cleaned_numbers.append(0)
                ds["data"] = cleaned_numbers

        # 6. Adjuntar metadatos de verificación (Problema 2 resuelto)
        if self.ultimo_resultado_verificado:
            if not datos_estructurados:
                datos_estructurados = {}
            datos_estructurados["verificado"] = True
            datos_estructurados["periodo"] = self.ultimo_periodo
            datos_estructurados["fuente"] = self.ultima_fuente
        elif self.ultimo_periodo:
            if not datos_estructurados:
                datos_estructurados = {}
            datos_estructurados["verificado"] = False
            datos_estructurados["periodo"] = self.ultimo_periodo
            datos_estructurados["fuente"] = self.ultima_fuente

        return texto_limpio, datos_estructurados

    def procesar_mensaje(self, chat_id: UUID, mensaje_usuario: str) -> dict[str, Any]:
        """
        Orquesta la conversación con Gemini usando HTTP REST puro vía httpx:
        - Cero dependencias externas incompatibles.
        - Soporta Function Calling nativo con PostgREST.
        - Reintento automático con backoff ante rate-limit o 503.
        """
        import time

        # Limpiar texto de dictado por voz si viene con texto basura (Problema 5 resuelto)
        mensaje_limpio = re.sub(
            r"^(?:🎙️?\s*escuchando(?:\s+voz|\s+tu\s+voz)?[\s,\.:-]*habla(?:\s+con\s+claridad|\s+con\s+naturalidad)?(?:[\s,\.:-]*ya)?)+",
            "",
            mensaje_usuario,
            flags=re.IGNORECASE,
        ).strip()
        if not mensaje_limpio:
            mensaje_limpio = mensaje_usuario.strip()

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
            contenido=mensaje_limpio,
            datos_estructurados=None,
            herramientas_usadas=None,
        )
        self.db.add(msg_user)
        self.db.flush()

        if chat.titulo == "Nueva conversación":
            titulo_auto = mensaje_limpio.strip()[:40]
            if len(mensaje_limpio.strip()) > 40:
                titulo_auto += "..."
            chat.titulo = titulo_auto

        if not self.api_key:
            texto_respuesta = (
                "⚠️ **Aviso del Sistema:** La clave `GEMINI_API_KEY` no está configurada en el servidor. "
                "Por favor, define la variable en el archivo `.env` del backend para activar las respuestas de IA."
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
                "id": str(msg_ia.id),
                "chat_id": str(chat.id),
                "rol": "assistant",
                "contenido": msg_ia.contenido,
                "datos_estructurados": None,
                "herramientas_usadas": None,
                "verificado": False,
                "created_at": msg_ia.created_at.isoformat(),
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
                    contents[-1]["parts"][0]["text"] += f"\n\n{turno['parts'][0]['text']}"

        # Agregar el mensaje actual del usuario garantizando alternancia
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"][0]["text"] += f"\n\n{mensaje_limpio}"
        else:
            contents.append({"role": "user", "parts": [{"text": mensaje_limpio}]})

        modelo_env = getattr(settings, "gemini_model", None)
        if modelo_env in ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"):
            modelo_env = "gemini-3.6-flash"

        lista_base = [
            modelo_env if modelo_env else "gemini-3.6-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash",
        ]
        modelos_candidatos = list(dict.fromkeys(lista_base))

        herramientas_ejecutadas: list[str] = []
        texto_final = ""
        errores_intentos: list[str] = []

        with httpx.Client(timeout=45.0) as client:
            for modelo in modelos_candidatos:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={self.api_key}"
                exito_modelo = False

                for intento in range(3):
                    try:
                        payload = {
                            "contents": contents,
                            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                            "tools": GEMINI_TOOLS_DECLARATION,
                            "generationConfig": {
                                "temperature": 0.2,
                                "maxOutputTokens": 4096,
                            },
                        }

                        # Bucle de Function Calling (máximo 5 iteraciones)
                        for iteracion in range(5):
                            res = client.post(url, json=payload)
                            if res.status_code != 200:
                                err_info = f"[{modelo}] HTTP {res.status_code}: {res.text[:120]}"
                                logger.warning("Gemini error intento %d: %s", intento + 1, err_info)
                                errores_intentos.append(err_info)
                                if res.status_code in (429, 500, 502, 503, 504) and intento < 2:
                                    time.sleep(1.5)
                                break

                            res_json = res.json()
                            candidates = res_json.get("candidates", [])
                            if not candidates:
                                err_info = f"[{modelo}] Sin candidatos en respuesta: {str(res_json)[:100]}"
                                logger.warning(err_info)
                                errores_intentos.append(err_info)
                                break

                            content_candidate = candidates[0].get("content", {})
                            parts = content_candidate.get("parts", [])

                            # Verificar si hay functionCall
                            function_calls = [p.get("functionCall") for p in parts if "functionCall" in p]
                            if not function_calls:
                                textos = [p.get("text", "") for p in parts if "text" in p]
                                texto_final = "\n".join(textos).strip()
                                exito_modelo = True
                                break

                            # Agregar el mensaje del modelo con sus functionCalls a contents
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

                            # Enviar respuestas de funciones
                            payload["contents"].append(
                                {
                                    "role": "user",
                                    "parts": response_parts,
                                }
                            )

                        if exito_modelo and texto_final:
                            break

                    except Exception as ex:
                        err_info = f"[{modelo}] Excepción intento {intento + 1}: {type(ex).__name__} {str(ex)[:120]}"
                        logger.warning(err_info)
                        errores_intentos.append(err_info)
                        if intento < 2:
                            time.sleep(1.0)
                        continue

                if texto_final:
                    break

        if not texto_final:
            detalle_fallos = " // ".join(errores_intentos) if errores_intentos else "Sin respuesta de modelos"
            texto_final = (
                f"El Agente Tridente IA no pudo completar la consulta en este momento.\n\n"
                f"> 🔍 **Diagnóstico de conexión:** `{detalle_fallos}`\n\n"
                f"Por favor verifica la conexión o intenta nuevamente en unos segundos."
            )

        texto_limpio, datos_estructurados = self._extraer_datos_estructurados(texto_final)
        es_verificado = bool(datos_estructurados and datos_estructurados.get("verificado") is True)

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
            "id": str(msg_ia.id),
            "chat_id": str(chat.id),
            "rol": "assistant",
            "contenido": msg_ia.contenido,
            "datos_estructurados": msg_ia.datos_estructurados,
            "herramientas_usadas": msg_ia.herramientas_usadas,
            "verificado": es_verificado,
            "created_at": msg_ia.created_at.isoformat(),
        }

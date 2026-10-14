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
Eres el **Agente Tridente IA**, el asistente inteligente de analítica comercial y abastecimiento de Distribuidora Tridente.
Tu objetivo es ayudar a los administradores a supervisar y optimizar el negocio:
- Consultar stock de productos, precios y estados.
- Analizar el historial y frecuencia de pedidos de clientes.
- Realizar análisis predictivos de abastecimiento (identificar qué productos se van a agotar pronto según la rotación de pedidos y sugerir cantidades de reposición).
- Generar métricas ejecutivas, resúmenes de facturación y rankings de ventas.

Tienes herramientas disponibles para consultar en tiempo real las tablas de productos y pedidos a través del servicio PostgREST/PostgreSQL:
1. `consultar_productos`: busca productos por nombre/código, stock o estado.
2. `consultar_pedidos_recientes`: consulta pedidos y compras de clientes en un rango de días.
3. `consultar_metricas_generales`: obtiene métricas consolidadas (top más vendidos, total facturado, stock crítico).

REGLAS FUNDAMENTALES:
1. Siempre que te pregunten sobre productos, stock, ventas, clientes o pedidos, DEBES utilizar las herramientas para consultar los datos reales antes de responder. No inventes datos.
2. Sé conciso, profesional y estratégico en tus conclusiones.
3. Si el usuario te pide un gráfico, visualización, comparativa o números para visualizar, DEBES incluir en tu respuesta un bloque JSON estructurado con el formato:

```json
{
  "type": "chart",
  "chartType": "bar",
  "title": "Top 5 Productos más Vendidos",
  "description": "Comparativa de unidades vendidas en los últimos 30 días",
  "data": {
    "labels": ["Producto A", "Producto B", "Producto C"],
    "datasets": [
      {
        "label": "Unidades Vendidas",
        "data": [120, 85, 43],
        "backgroundColor": ["#0ea5e9", "#10b981", "#f59e0b"]
      }
    ]
  }
}
```

4. Si realizas un análisis predictivo de compras, además de tu explicación, incluye un bloque estructurado:
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
"""

GEMINI_TOOLS_DECLARATION = [
    {
        "functionDeclarations": [
            {
                "name": "consultar_productos",
                "description": "Consulta productos en el catálogo de Distribuidora Tridente por término de búsqueda, stock o estado activo vía PostgREST.",
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
                "description": "Consulta los pedidos recientes y sus detalles de venta vía PostgREST.",
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


class AgenteIAService:
    def __init__(self, db: Session, usuario: Usuario):
        self.db = db
        self.usuario = usuario
        self.postgrest = PostgrestService(db)
        self.api_key = settings.gemini_api_key

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
        """Extrae bloques de json de tipo 'chart' o 'prediction'."""
        datos_estructurados = None
        bloques = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", texto)
        for b in bloques:
            try:
                parsed = json.loads(b)
                if isinstance(parsed, dict) and parsed.get("type") in ("chart", "prediction"):
                    datos_estructurados = parsed
                    break
            except Exception:
                continue

        if not datos_estructurados:
            match = re.search(r'(\{\s*"type"\s*:\s*"(?:chart|prediction)"[\s\S]*?\n\})', texto)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, dict):
                        datos_estructurados = parsed
                except Exception:
                    pass

        return texto, datos_estructurados

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
                "created_at": msg_ia.created_at.isoformat(),
            }

        # Armar historial de contents para la API de Gemini
        contents: list[dict[str, Any]] = []
        for m in chat.mensajes:
            if m.id == msg_user.id:
                continue
            role = "user" if m.rol == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.contenido}]})
        contents.append({"role": "user", "parts": [{"text": mensaje_usuario}]})

        modelos_candidatos = [
            "gemini-flash-latest",
            "gemini-pro-latest",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]

        herramientas_ejecutadas: list[str] = []
        texto_final = ""

        with httpx.Client(timeout=30.0) as client:
            for modelo in modelos_candidatos:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={self.api_key}"
                try:
                    payload = {
                        "contents": contents,
                        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                        "tools": GEMINI_TOOLS_DECLARATION,
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 2048,
                        },
                    }

                    # Bucle de Function Calling (máximo 4 iteraciones)
                    for _ in range(4):
                        res = client.post(url, json=payload)
                        if res.status_code != 200:
                            logger.warning("Gemini REST error %s: %s", res.status_code, res.text[:200])
                            break

                        res_json = res.json()
                        candidates = res_json.get("candidates", [])
                        if not candidates:
                            break

                        content_candidate = candidates[0].get("content", {})
                        parts = content_candidate.get("parts", [])

                        # Verificar si hay functionCall
                        function_calls = [p.get("functionCall") for p in parts if "functionCall" in p]
                        if not function_calls:
                            # Tenemos respuesta de texto final
                            textos = [p.get("text", "") for p in parts if "text" in p]
                            texto_final = "\n".join(textos).strip()
                            break

                        # Ejecutar llamadas a herramientas y enviar respuestas a Gemini
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

                        # Enviar las respuestas de las funciones
                        payload["contents"].append(
                            {
                                "role": "user",
                                "parts": response_parts,
                            }
                        )

                    if texto_final:
                        break

                except Exception as ex:
                    logger.warning("Fallo llamando a modelo %s: %s", modelo, str(ex))
                    continue

        if not texto_final:
            texto_final = (
                "El Agente Tridente IA no pudo completar la consulta en este momento. "
                "Por favor verifica la conexión o intenta nuevamente en unos segundos."
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
            "id": str(msg_ia.id),
            "chat_id": str(chat.id),
            "rol": "assistant",
            "contenido": msg_ia.contenido,
            "datos_estructurados": msg_ia.datos_estructurados,
            "herramientas_usadas": msg_ia.herramientas_usadas,
            "created_at": msg_ia.created_at.isoformat(),
        }

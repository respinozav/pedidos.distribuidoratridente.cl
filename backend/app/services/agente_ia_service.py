import json
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.entities import IAChat, IAMensaje, Usuario
from app.services.postgrest_service import PostgrestService

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_INSTRUCTION = """
Eres el **Agente Tridente IA**, el asistente inteligente de analítica y gestión comercial de Distribuidora Tridente.
Tu objetivo es ayudar a los administradores a supervisar y optimizar el negocio:
- Consultar stock de productos, precios y estados.
- Analizar el historial y frecuencia de pedidos de clientes.
- Realizar análisis predictivos de abastecimiento (identificar qué productos se van a agotar pronto según la rotación de pedidos y sugerir cantidades de reposición).
- Generar métricas ejecutivas, resúmenes de facturación y rankings de ventas.

Tienes a tu disposición herramientas (Function Calling) para consultar en tiempo real las tablas de productos y pedidos a través del servicio PostgREST/PostgreSQL:
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
  "chartType": "bar", // o "line", "pie", "doughnut"
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
Puedes incluir texto explicativo en formato Markdown antes o después del bloque JSON.
"""


class AgenteIAService:
    def __init__(self, db: Session, usuario: Usuario):
        self.db = db
        self.usuario = usuario
        self.postgrest = PostgrestService(db)
        self.api_key = settings.gemini_api_key

    def _get_genai_client(self) -> genai.Client:
        return genai.Client(api_key=self.api_key)

    def ejecutar_herramienta(self, nombre: str, args: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta la función solicitada por Gemini vía PostgREST."""
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
        Detecta bloques de json de tipo 'chart' o 'prediction' dentro de la respuesta
        y los extrae para el frontend.
        """
        datos_estructurados = None
        # Buscar bloques ```json { ... } ```
        bloques = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", texto)
        for b in bloques:
            try:
                parsed = json.loads(b)
                if isinstance(parsed, dict) and parsed.get("type") in ("chart", "prediction"):
                    datos_estructurados = parsed
                    break
            except Exception:
                continue

        # Si no encontró en bloques de código, buscar cualquier JSON con "type": "chart"
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
        Orquesta la conversación con Gemini:
        1. Guarda el mensaje del usuario.
        2. Configura tools de Function Calling.
        3. Realiza la llamada a Gemini y maneja tool calls iterativamente.
        4. Extrae gráficos estructurados y guarda respuesta del asistente.
        """
        # 1. Obtener o validar el chat
        chat = self.db.scalar(
            select(IAChat)
            .options(selectinload(IAChat.mensajes))
            .where(IAChat.id == chat_id, IAChat.usuario_id == self.usuario.id)
        )
        if not chat:
            raise ValueError("Chat no encontrado o no autorizado")

        # 2. Guardar mensaje del usuario
        msg_user = IAMensaje(
            chat_id=chat.id,
            rol="user",
            contenido=mensaje_usuario,
            datos_estructurados=None,
            herramientas_usadas=None,
        )
        self.db.add(msg_user)
        self.db.flush()

        # Si el chat aún tiene título por defecto y es el primer mensaje, generamos un título breve
        if chat.titulo == "Nueva conversación":
            titulo_auto = mensaje_usuario.strip()[:40]
            if len(mensaje_usuario.strip()) > 40:
                titulo_auto += "..."
            chat.titulo = titulo_auto

        # 3. Preparar historial para Gemini
        historial_previo = [
            types.Content(
                role="user" if m.rol == "user" else "model",
                parts=[types.Part.from_text(text=m.contenido)],
            )
            for m in chat.mensajes
            if m.id != msg_user.id
        ]
        historial_previo.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=mensaje_usuario)],
            )
        )

        # 4. Definir herramientas como funciones de Python
        def consultar_productos(
            termino_busqueda: str = "",
            solo_activos: bool = True,
            ordenar_por_stock_asc: bool = False,
            limite: int = 35,
        ) -> str:
            """Consulta productos en el catálogo de Distribuidora Tridente vía PostgREST."""
            data = self.ejecutar_herramienta(
                "consultar_productos",
                {
                    "termino_busqueda": termino_busqueda,
                    "solo_activos": solo_activos,
                    "ordenar_por_stock_asc": ordenar_por_stock_asc,
                    "limite": limite,
                },
            )
            return json.dumps(data, ensure_ascii=False)

        def consultar_pedidos_recientes(
            dias_historial: int = 30,
            estado_filtro: str = "",
            limite: int = 35,
        ) -> str:
            """Consulta pedidos recientes y sus detalles de venta vía PostgREST."""
            data = self.ejecutar_herramienta(
                "consultar_pedidos_recientes",
                {
                    "dias_historial": dias_historial,
                    "estado_filtro": estado_filtro or None,
                    "limite": limite,
                },
            )
            return json.dumps(data, ensure_ascii=False)

        def consultar_metricas_generales(dias: int = 30) -> str:
            """Obtiene métricas de negocio: productos más vendidos, stock crítico y facturación total."""
            data = self.ejecutar_herramienta(
                "consultar_metricas_generales",
                {"dias": dias},
            )
            return json.dumps(data, ensure_ascii=False)

        herramientas_list = [
            consultar_productos,
            consultar_pedidos_recientes,
            consultar_metricas_generales,
        ]

        herramientas_ejecutadas: list[str] = []
        respuesta_texto = ""
        datos_estructurados = None

        modelos_candidatos = [
            settings.gemini_model or "gemini-3.5-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-3.6-flash",
        ]

        if not self.api_key:
            respuesta_texto = (
                "⚠️ **Aviso del Sistema:** La clave `GEMINI_API_KEY` no está configurada en el servidor. "
                "Por favor, define la variable en el archivo `.env` del backend para activar las respuestas de IA."
            )
        else:
            client = self._get_genai_client()
            for modelo in modelos_candidatos:
                try:
                    config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=herramientas_list,
                        temperature=0.3,
                    )
                    # Realizar la llamada a Gemini (el SDK de google-genai maneja function calling automáticamente si se pasan funciones)
                    response = client.models.generate_content(
                        model=modelo,
                        contents=historial_previo,
                        config=config,
                    )

                    # Verificar si hubo llamadas a herramientas registradas
                    if hasattr(response, "function_calls") and response.function_calls:
                        for fc in response.function_calls:
                            herramientas_ejecutadas.append(fc.name)

                    respuesta_texto = response.text or ""
                    break
                except Exception as ex:
                    err_msg = str(ex)
                    logger.warning("Error llamando a Gemini modelo %s: %s", modelo, err_msg)
                    if "503" in err_msg or "high demand" in err_msg or "404" in err_msg:
                        # Probar siguiente modelo
                        continue
                    # Si hubo otro error pero tenemos respuesta previa
                    respuesta_texto = (
                        f"Ocurrió un error al procesar tu solicitud con Gemini ({err_msg[:120]}). "
                        "Por favor intenta de nuevo en unos momentos."
                    )
                    break

            if not respuesta_texto:
                respuesta_texto = (
                    "El servicio de IA se encuentra temporalmente con alta demanda en este momento. "
                    "Por favor intenta enviar tu mensaje nuevamente en unos segundos."
                )

        # 5. Extraer cualquier gráfico o predicción estructurada
        texto_limpio, datos_estructurados = self._extraer_datos_estructurados(respuesta_texto)

        # 6. Guardar mensaje de la IA en la base de datos
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

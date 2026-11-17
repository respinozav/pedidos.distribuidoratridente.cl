import re
import unicodedata
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Cliente, Producto
from app.schemas.dto import (
    DictadoClienteCandidato,
    DictadoItemInterpretado,
    DictadoInterpretadoOutput,
    DictadoProductoMatch,
)
from app.services.pricing import customer_product_box_price, customer_product_price


def pesos_a_voz(monto: Decimal | int | float) -> str:
    """Convierte un monto numérico a formato ideal para síntesis de voz (TTS)."""
    try:
        val = int(round(float(monto)))
        return f"${val:,}".replace(",", ".")
    except Exception:
        return f"${monto}"

NUMEROS_PALABRAS: dict[str, int] = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "quinientos": 500,
    "mil": 1000,
}

PALABRAS_CAJA: set[str] = {
    "caja",
    "cajas",
    "carton",
    "cartones",
    "pack",
    "packs",
    "paquete",
    "paquetes",
    "display",
    "displays",
    "bulto",
    "bultos",
    "tira",
    "tiras",
}

PALABRAS_UNIDAD: set[str] = {
    "unidad",
    "unidades",
    "un",
    "uds",
    "suelto",
    "sueltos",
    "pieza",
    "piezas",
}

STOPWORDS: set[str] = {
    "de",
    "del",
    "la",
    "las",
    "el",
    "los",
    "un",
    "una",
    "unos",
    "unas",
    "por",
    "para",
    "con",
    "sin",
    "en",
    "y",
    "o",
    "al",
    "favor",
    "quiero",
    "agrega",
    "agregar",
    "dame",
    "pon",
    "poner",
    "siguiente",
    "siguientes",
    "productos",
    "producto",
}


CLIENTE_FILLER_WORDS: set[str] = {
    "de",
    "del",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "don",
    "dona",
    "sr",
    "sra",
    "almacen",
    "almacenes",
    "minimarket",
    "market",
    "botilleria",
    "botillerias",
    "comercial",
    "distribuidora",
    "negocio",
    "local",
    "tienda",
    "spa",
    "ltda",
    "eirl",
    "sociedad",
}


def normalizar_texto(texto: str) -> str:
    """Normaliza un texto eliminando tildes, caracteres especiales y pasando a minúsculas."""
    if not texto:
        return ""
    # Quitar tildes
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Limpiar signos y caracteres innecesarios
    limpio = re.sub(r"[^a-zA-Z0-9\s]", " ", sin_tildes.lower())
    return re.sub(r"\s+", " ", limpio).strip()


class AsistentePedidoService:
    @classmethod
    def detectar_comando(cls, texto_normalizado: str) -> tuple[str | None, str | None]:
        """
        Detecta comandos por voz:
        - 'finalizar', 'terminar', 'listo', 'eso es todo', 'cerrar pedido', 'revisar' -> ('finalizar', None)
        - 'confirmar', 'emitir', 'emitir pedido', 'enviar pedido', 'si confirmar', 'dale' -> ('confirmar', None)
        - 'eliminar <producto>', 'quita <producto>', 'borra <producto>' -> ('eliminar', producto)
        - 'vaciar', 'vaciar pedido', 'borrar todo', 'empezar de nuevo', 'reiniciar' -> ('vaciar', None)
        """
        t = texto_normalizado.strip()
        if not t:
            return None, None

        # Comandos de confirmación final
        patrones_confirmar = [
            r"^(?:si\s+)?(?:confirmar|emitir|enviar)(?:\s+el)?(?:\s+pedido)?$",
            r"^(?:si|dale|proceder|listo\s+para\s+emitir|emitelo|confirmalo)$",
            r"^si\s+por\s+favor$",
        ]
        for pat in patrones_confirmar:
            if re.search(pat, t):
                return "confirmar", None

        # Comandos de finalización / revisión
        patrones_finalizar = [
            r"^(?:finalizar|terminar|cerrar)(?:\s+el)?(?:\s+pedido)?$",
            r"^(?:listo|eso\s+es\s+todo|no\s+mas|nada\s+mas|ya\s+termine|completar\s+pedido)$",
            r"^(?:revisar|ver\s+resumen)$",
        ]
        for pat in patrones_finalizar:
            if re.search(pat, t):
                return "finalizar", None

        # Comandos de eliminación
        m_eliminar = re.search(
            r"^(?:eliminar|quita|quitar|borra|borrar|saca|sacar)\s+(?:el\s+|la\s+|los\s+|las\s+)?(.+)$",
            t,
        )
        if m_eliminar:
            prod_term = m_eliminar.group(1).strip()
            prod_term = re.sub(r"\s+del\s+pedido$", "", prod_term).strip()
            if prod_term:
                return "eliminar", prod_term

        # Comandos de vaciado / reinicio
        if t in {
            "vaciar",
            "vaciar pedido",
            "borrar todo",
            "empezar de nuevo",
            "reiniciar",
            "limpiar pedido",
        }:
            return "vaciar", None

        return None, None

    @classmethod
    def detectar_candidatos_cliente(
        cls, texto: str, db: Session
    ) -> tuple[Cliente | None, str, list[Cliente]]:
        """
        Detecta cliente a partir del dictado y devuelve (mejor_cliente, texto_restante, lista_candidatos).
        Permite tanto frases con prefijo ('pedido para X') como frases directas ('X').
        """
        patrones = [
            r"(?:generame|genera|crear|haz|hacer)?\s*(?:un\s+)?pedido\s+(?:a\s+nombre\s+de|para\s+el\s+cliente|para\s+cliente|para)\s+([a-zA-Z0-9\s\.\-]+?)(?:\s+(?:los\s+siguientes\s+productos|los\s+siguientes|con\s+los|y\s+los|productos|con|que\s+lleve|:)|$)",
            r"(?:a\s+nombre\s+de|cliente)\s+([a-zA-Z0-9\s\.\-]+?)(?:\s+(?:los\s+siguientes\s+productos|los\s+siguientes|con\s+los|y\s+los|productos|con|que\s+lleve|:)|$)",
        ]

        texto_restante = texto
        candidato_nombre = ""

        for patron in patrones:
            match = re.search(patron, texto, flags=re.IGNORECASE)
            if match:
                candidato_nombre = match.group(1).strip()
                texto_restante = texto[match.end():].strip()
                # Limpiar residuos iniciales si quedaron
                texto_restante = re.sub(r"^(?:productos|los siguientes|los siguientes productos|con|y)\s*", "", texto_restante, flags=re.IGNORECASE).strip()
                break

        # Si no hubo prefijo explícito pero el texto es corto, evaluarlo directamente como candidato
        if not candidato_nombre and len(texto.strip()) <= 60:
            candidato_nombre = texto.strip()
            texto_restante = ""

        if not candidato_nombre or len(candidato_nombre) < 2:
            return None, texto, []

        clientes_activos = list(
            db.scalars(
                select(Cliente)
                .options(selectinload(Cliente.direcciones))
                .where(Cliente.activo.is_(True), Cliente.eliminado_at.is_(None))
            )
        )

        cand_norm = normalizar_texto(candidato_nombre)
        cand_tokens = set(cand_norm.split())
        cand_significativos = {t for t in cand_tokens if t not in CLIENTE_FILLER_WORDS} or cand_tokens
        cand_rut_clean = re.sub(r"[^0-9k]", "", cand_norm)

        ranking: list[tuple[float, Cliente]] = []

        for c in clientes_activos:
            score = 0.0
            alias_val = getattr(c, "alias", None) or ""
            nombre_val = getattr(c, "nombre", None) or ""
            rut_val = getattr(c, "rut", None) or ""
            celular_val = getattr(c, "celular", None) or ""

            alias_norm = normalizar_texto(alias_val)
            nombre_norm = normalizar_texto(nombre_val)
            rut_norm = normalizar_texto(rut_val).replace("-", "").replace(".", "")
            rut_clean = re.sub(r"[^0-9k]", "", rut_norm)
            celular_clean = re.sub(r"[^0-9]", "", celular_val)

            # 1. Coincidencia exacta de alias o nombre
            if cand_norm == alias_norm or cand_norm == nombre_norm:
                score = 100.0
            elif cand_norm in alias_norm or alias_norm in cand_norm:
                score = max(score, 90.0)
            elif cand_norm in nombre_norm or nombre_norm in cand_norm:
                score = max(score, 85.0)

            # 2. Coincidencia por RUT
            if cand_rut_clean and rut_clean and len(cand_rut_clean) >= 4:
                if cand_rut_clean == rut_clean:
                    score = max(score, 100.0)
                elif cand_rut_clean in rut_clean or rut_clean in cand_rut_clean:
                    score = max(score, 95.0)

            # 3. Coincidencia por Celular
            if celular_clean and len(cand_rut_clean) >= 6 and cand_rut_clean in celular_clean:
                score = max(score, 92.0)

            # 4. Coincidencia por tokens significativos
            alias_tokens = set(alias_norm.split()).union(set(nombre_norm.split()))
            alias_significativos = {t for t in alias_tokens if t not in CLIENTE_FILLER_WORDS} or alias_tokens
            if cand_significativos and alias_significativos:
                comunes = cand_significativos.intersection(alias_significativos)
                if comunes:
                    pct = (len(comunes) / len(cand_significativos)) * 85.0
                    score = max(score, pct)

            if score >= 35.0:
                ranking.append((score, c))

        ranking.sort(key=lambda x: x[0], reverse=True)

        if not ranking:
            return None, texto, []

        top_score, top_cliente = ranking[0]
        if top_score >= 70.0:
            if len(ranking) == 1 or (top_score - ranking[1][0] >= 12.0):
                return top_cliente, texto_restante, []

        candidatos = [c for _, c in ranking[:4]]
        return None, texto_restante, candidatos

    @classmethod
    def detectar_cliente(cls, texto: str, db: Session) -> tuple[Cliente | None, str]:
        """
        Retorna (Cliente encontrado o None, texto restante).
        Mantiene compatibilidad estricta con llamados existentes.
        """
        cliente, texto_rest, _ = cls.detectar_candidatos_cliente(texto, db)
        return cliente, texto_rest if cliente else texto

    @classmethod
    def segmentar_clausulas(cls, texto: str) -> list[str]:
        """Divide el dictado en frases individuales correspondientes a productos."""
        # Reemplazar separadores comunes por coma
        reemplazos = [
            (r"\b(?:y\s+ademas|ademas|tambien|con|y\s+despues|despues|y\s+luego|luego)\b", ","),
            (r"\s+(?:y|e)\s+", ","),
            (r";", ","),
            (r"\n+", ","),
            (r"\.+", ","),
        ]
        t = texto
        for pat, repl in reemplazos:
            t = re.sub(pat, repl, t, flags=re.IGNORECASE)

        partes = [p.strip() for p in t.split(",") if p.strip()]
        return partes

    @classmethod
    def extraer_cantidad_y_empaque_detallado(cls, frase: str) -> tuple[int, str, str, bool]:
        """
        Extrae la cantidad numérica, tipo de empaque ('unidad' o 'caja'), término limpio y si la cantidad fue explícita.
        Retorna (cantidad, tipo_empaque, termino_limpio, cantidad_explicita).
        """
        texto_norm = normalizar_texto(frase)
        if not texto_norm:
            return 1, "unidad", "", False

        cantidad = 1
        tipo_empaque = "unidad"
        sub_eliminado = None

        patron_numeros = r"(?:\d+|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|veinticinco|treinta|cincuenta|cien)"
        patron_cajas = r"(?:cajas?|carton(?:es)?|packs?|paquetes?|displays?|bultos?|tiras?)"
        patron_unidades = r"(?:unidad(?:es)?|un|uds|piezas?|sueltos?)"

        # 1. Caso: <numero> <caja/carton> (ej: "2 cartones", "1 caja", "dos paquetes")
        m_caja = re.search(rf"\b({patron_numeros})\s+({patron_cajas})\b", texto_norm)
        if m_caja:
            num_str = m_caja.group(1)
            cantidad = int(num_str) if num_str.isdigit() else NUMEROS_PALABRAS.get(num_str, 1)
            tipo_empaque = "caja"
            sub_eliminado = m_caja.group(0)

        # 2. Caso: <numero> <unidad> (ej: "5 unidades", "10 un")
        if not sub_eliminado:
            m_uni = re.search(rf"\b({patron_numeros})\s+({patron_unidades})\b", texto_norm)
            if m_uni:
                num_str = m_uni.group(1)
                cantidad = int(num_str) if num_str.isdigit() else NUMEROS_PALABRAS.get(num_str, 1)
                tipo_empaque = "unidad"
                sub_eliminado = m_uni.group(0)

        # 3. Caso: <caja/carton> <numero> (ej: "carton 2", "cajas 3")
        if not sub_eliminado:
            m_inv = re.search(rf"\b({patron_cajas})\s+({patron_numeros})\b", texto_norm)
            if m_inv:
                num_str = m_inv.group(2)
                cantidad = int(num_str) if num_str.isdigit() else NUMEROS_PALABRAS.get(num_str, 1)
                tipo_empaque = "caja"
                sub_eliminado = m_inv.group(0)

        # 4. Caso: Solo menciona caja/carton sin número explícito (ej: "un carton" o "en caja")
        if not sub_eliminado:
            m_solocaja = re.search(rf"\b({patron_cajas})\b", texto_norm)
            if m_solocaja:
                tipo_empaque = "caja"
                sub_eliminado = m_solocaja.group(0)

        # 5. Caso: Número al final absoluto de la frase (ej: "kent actron 3")
        if not sub_eliminado:
            m_final = re.search(rf"\b({patron_numeros})\s*$", texto_norm)
            if m_final:
                num_str = m_final.group(1)
                cantidad = int(num_str) if num_str.isdigit() else NUMEROS_PALABRAS.get(num_str, 1)
                sub_eliminado = m_final.group(0)

        # 6. Caso: Número al inicio absoluto de la frase (ej: "3 kent actron")
        if not sub_eliminado:
            m_inicio = re.search(rf"^\s*({patron_numeros})\s+", texto_norm)
            if m_inicio:
                num_str = m_inicio.group(1)
                cantidad = int(num_str) if num_str.isdigit() else NUMEROS_PALABRAS.get(num_str, 1)
                sub_eliminado = m_inicio.group(0)

        cantidad_explicita = bool(sub_eliminado)

        # Limpiar la frase de la cantidad/empaque extraído
        if sub_eliminado:
            texto_limpio = texto_norm.replace(sub_eliminado, " ", 1)
        else:
            texto_limpio = texto_norm

        tokens = texto_limpio.split()
        tokens_finales = [t for t in tokens if t not in STOPWORDS]
        termino_final = " ".join(tokens_finales).strip()

        return max(1, cantidad), tipo_empaque, termino_final, cantidad_explicita

    @classmethod
    def extraer_cantidad_y_empaque(cls, frase: str) -> tuple[int, str, str]:
        """
        Mantiene compatibilidad hacia atrás devolviendo (cantidad, tipo_empaque, termino_limpio).
        """
        cant, emp, term, _ = cls.extraer_cantidad_y_empaque_detallado(frase)
        return cant, emp, term

    @classmethod
    def buscar_producto_en_catalogo(
        cls,
        termino: str,
        productos_activos: list[Producto],
        cliente: Cliente | None = None,
    ) -> tuple[str, DictadoProductoMatch | None, list[DictadoProductoMatch]]:
        """
        Busca en el catálogo el término indicado con tolerancia a fallos y ranking de relevancia.
        Retorna (estado: 'exacto' | 'multiple' | 'no_encontrado', producto_seleccionado, opciones).
        """
        if not termino or len(termino) < 2:
            return "no_encontrado", None, []

        term_norm = normalizar_texto(termino)
        term_tokens = set(term_norm.split())

        candidatos: list[tuple[float, Producto]] = []

        for p in productos_activos:
            p_codigo_norm = normalizar_texto(p.codigo or "")
            p_nombre_norm = normalizar_texto(p.nombre or "")
            p_tokens = set(p_nombre_norm.split()).union(set(p_codigo_norm.split()))

            score = 0.0

            # 1. Coincidencia exacta de código
            if term_norm == p_codigo_norm:
                score = 100.0
            # 2. Coincidencia exacta de nombre
            elif term_norm == p_nombre_norm:
                score = 98.0
            # 3. Substring completo de nombre
            elif term_norm in p_nombre_norm:
                score = 85.0 + (len(term_norm) / max(len(p_nombre_norm), 1)) * 10.0
            elif p_nombre_norm in term_norm:
                score = 80.0
            else:
                # 4. Coincidencia por tokens (palabras clave compartidas)
                if term_tokens and p_tokens:
                    comunes = term_tokens.intersection(p_tokens)
                    if comunes:
                        ratio_cubierto = len(comunes) / len(term_tokens)
                        score = ratio_cubierto * 80.0
                        # Bonificación si coincide la primera palabra (marca/categoría principal)
                        primer_term = list(term_tokens)[0] if term_tokens else ""
                        if primer_term in p_tokens:
                            score += 5.0

            if score >= 40.0:
                candidatos.append((score, p))

        # Ordenar candidatos de mayor a menor puntuación
        candidatos.sort(key=lambda x: x[0], reverse=True)

        if not candidatos:
            return "no_encontrado", None, []

        def armar_dto(prod: Producto, sc: float) -> DictadoProductoMatch:
            # Calcular precio acorde al cliente si existe
            precio_aplicado = prod.precio
            precio_caja_aplicado = prod.precio_caja
            if cliente:
                try:
                    precio_aplicado = customer_product_price(prod, cliente)
                    precio_caja_calc = customer_product_box_price(prod, cliente)
                    if precio_caja_calc is not None:
                        precio_caja_aplicado = precio_caja_calc
                except Exception:
                    pass

            return DictadoProductoMatch(
                id=prod.id,
                codigo=prod.codigo,
                nombre=prod.nombre,
                precio=precio_aplicado,
                afecto=bool(prod.afecto),
                tiene_caja=bool(prod.tiene_caja),
                cantidad_caja=prod.cantidad_caja,
                precio_caja=precio_caja_aplicado,
                stock=prod.cantidad or 0,
                score=round(sc, 1),
            )

        top_score, top_prod = candidatos[0]

        # Si el mejor resultado tiene score alto y supera con claridad al segundo:
        if top_score >= 82.0:
            if len(candidatos) == 1 or (top_score - candidatos[1][0] >= 15.0):
                return "exacto", armar_dto(top_prod, top_score), []

        # Si hay múltiples coincidencias con puntajes cercanos o score moderado:
        opciones_dto = [armar_dto(p, sc) for sc, p in candidatos[:5]]
        return "multiple", None, opciones_dto

    @classmethod
    def interpretar_dictado(
        cls,
        texto: str,
        cliente_id: UUID | None,
        db: Session,
        estado_conversacion: str | None = None,
    ) -> DictadoInterpretadoOutput:
        """
        Orquesta la interpretación de voz/texto para armado de pedidos:
        - Detecta comandos de voz (finalizar, confirmar, eliminar, vaciar).
        - Detecta cliente si viene en la frase o si estamos en paso de cliente.
        - Segmenta y procesa cada producto dictado con cantidad y unidad/caja.
        - Detecta productos que requieren confirmación de cantidad o desambiguación.
        - Retorna mensajes de síntesis de voz (TTS) optimizados en lenguaje natural.
        """
        texto_limpio = texto.strip()
        texto_norm = normalizar_texto(texto_limpio)

        # 1. Detección de Comandos por Voz
        cmd, param = cls.detectar_comando(texto_norm)
        if cmd == "finalizar":
            return DictadoInterpretadoOutput(
                cliente_detectado_id=cliente_id,
                comando_detectado="finalizar",
                estado_conversacion="CONFIRMACION_FINAL",
                mensaje_asistente="Pedido listo para revisión final. ¿Deseas confirmar la emisión a Defontana?",
                mensaje_voz="¿Deseas confirmar la emisión del pedido a Defontana?",
            )
        elif cmd == "confirmar":
            return DictadoInterpretadoOutput(
                cliente_detectado_id=cliente_id,
                comando_detectado="confirmar",
                estado_conversacion="CONFIRMANDO",
                mensaje_asistente="Confirmando y emitiendo pedido a Defontana...",
                mensaje_voz="Emitiendo pedido a Defontana.",
            )
        elif cmd == "eliminar":
            return DictadoInterpretadoOutput(
                cliente_detectado_id=cliente_id,
                comando_detectado="eliminar",
                parametro_comando=param,
                estado_conversacion=estado_conversacion or "ESPERANDO_PRODUCTOS",
                mensaje_asistente=f"Eliminando producto '{param}' del pedido.",
                mensaje_voz=f"Eliminado {param} del pedido.",
            )
        elif cmd == "vaciar":
            return DictadoInterpretadoOutput(
                cliente_detectado_id=cliente_id,
                comando_detectado="vaciar",
                estado_conversacion="ESPERANDO_PRODUCTOS",
                mensaje_asistente="Se ha vaciado el borrador del pedido.",
                mensaje_voz="He vaciado el borrador del pedido. ¿Qué productos deseas agregar?",
            )

        cliente: Cliente | None = None
        if cliente_id:
            cliente = db.get(Cliente, cliente_id)

        texto_trabajo = texto_limpio
        cliente_detectado_id = None
        cliente_detectado_nombre = None
        clientes_candidatos_dto: list[DictadoClienteCandidato] = []

        # 2. Detección de Cliente si no venía seleccionado
        if not cliente:
            cliente_detectado, texto_restante, cands = cls.detectar_candidatos_cliente(texto_trabajo, db)
            if cliente_detectado:
                cliente = cliente_detectado
                cliente_detectado_id = cliente.id
                cliente_detectado_nombre = cliente.alias or cliente.nombre or cliente.rut
                texto_trabajo = texto_restante
                # Si el usuario solo dictó el cliente y nada más
                if not texto_restante or len(texto_restante) < 3:
                    return DictadoInterpretadoOutput(
                        cliente_detectado_id=cliente.id,
                        cliente_detectado_nombre=cliente_detectado_nombre,
                        estado_conversacion="ESPERANDO_PRODUCTOS",
                        mensaje_asistente=f"Cliente '{cliente_detectado_nombre}' seleccionado. ¿Qué productos deseas agregar?",
                        mensaje_voz=f"Cliente {cliente_detectado_nombre} seleccionado. ¿Qué productos y cantidades deseas agregar?",
                    )
            elif cands:
                # Múltiples candidatos encontrados
                cands_dto = [
                    DictadoClienteCandidato(id=c.id, nombre=c.nombre, alias=c.alias, rut=c.rut)
                    for c in cands
                ]
                nombres = " o ".join([c.alias or c.nombre for c in cands[:3]])
                return DictadoInterpretadoOutput(
                    clientes_candidatos=cands_dto,
                    estado_conversacion="ESPERANDO_CLIENTE",
                    mensaje_asistente=f"Encontré varias opciones de cliente: {nombres}. Por favor indica cuál deseas.",
                    mensaje_voz=f"Encontré varias opciones: {nombres}. ¿Cuál de ellos prefieres?",
                )

        # 3. Caso especial: si estamos esperando cantidad
        if estado_conversacion == "ESPERANDO_CANTIDAD":
            cant_resp, emp_resp, _, explicita_resp = cls.extraer_cantidad_y_empaque_detallado(texto_trabajo)
            if explicita_resp or cant_resp > 1 or emp_resp == "caja":
                return DictadoInterpretadoOutput(
                    cliente_detectado_id=cliente_id or (cliente.id if cliente else None),
                    cliente_detectado_nombre=cliente_detectado_nombre or (cliente.alias or cliente.nombre if cliente else None),
                    items=[
                        DictadoItemInterpretado(
                            termino_original=texto_trabajo,
                            cantidad=cant_resp,
                            tipo_empaque=emp_resp,
                            estado="exacto",
                            cantidad_explicita=True,
                        )
                    ],
                    estado_conversacion="ESPERANDO_PRODUCTOS",
                    mensaje_asistente=f"Cantidad registrada: {cant_resp} ({emp_resp}).",
                    mensaje_voz=f"Registradas {cant_resp} {'cajas' if emp_resp == 'caja' else 'unidades'}.",
                )

        # 4. Obtener catálogo y procesar productos
        productos_activos = list(
            db.scalars(
                select(Producto)
                .options(selectinload(Producto.categoria))
                .where(Producto.activo.is_(True), Producto.eliminado_at.is_(None))
                .order_by(Producto.nombre.asc())
            )
        )

        clausulas = cls.segmentar_clausulas(texto_trabajo)
        items_interpretados: list[DictadoItemInterpretado] = []

        total_exactos = 0
        total_multiples = 0
        total_no_encontrados = 0

        for frase in clausulas:
            cant, empaque, termino, cantidad_explicita = cls.extraer_cantidad_y_empaque_detallado(frase)
            if not termino or len(termino) < 2:
                continue

            estado, prod_exacto, opciones = cls.buscar_producto_en_catalogo(
                termino, productos_activos, cliente
            )

            if estado == "exacto":
                total_exactos += 1
            elif estado == "multiple":
                total_multiples += 1
            else:
                total_no_encontrados += 1

            items_interpretados.append(
                DictadoItemInterpretado(
                    termino_original=frase,
                    cantidad=cant,
                    tipo_empaque=empaque,
                    estado=estado,
                    producto=prod_exacto,
                    opciones=opciones,
                    cantidad_explicita=cantidad_explicita,
                )
            )

        # Caso: Usuario dictó 1 solo producto sin especificar cantidad explícita (ej: "bolsa taco transparente")
        if len(items_interpretados) == 1:
            solo_item = items_interpretados[0]
            if solo_item.estado == "exacto" and not solo_item.cantidad_explicita and solo_item.producto:
                return DictadoInterpretadoOutput(
                    cliente_detectado_id=cliente_detectado_id or (cliente.id if cliente else None),
                    cliente_detectado_nombre=cliente_detectado_nombre or (cliente.alias or cliente.nombre if cliente else None),
                    items=items_interpretados,
                    producto_pendiente_cantidad=solo_item.producto,
                    estado_conversacion="ESPERANDO_CANTIDAD",
                    mensaje_asistente=f"Encontré '{solo_item.producto.nombre}'. ¿Cuántas unidades o paquetes deseas agregar?",
                    mensaje_voz=f"Encontré {solo_item.producto.nombre}. ¿Cuántas unidades o paquetes deseas agregar?",
                )

        # Generar mensajes para el asistente y síntesis de voz (TTS)
        partes_resumen = []
        if total_exactos > 0:
            partes_resumen.append(f"{total_exactos} producto{'s' if total_exactos > 1 else ''} agregado{'s' if total_exactos > 1 else ''}")
        if total_multiples > 0:
            partes_resumen.append(f"{total_multiples} con opciones para elegir")
        if total_no_encontrados > 0:
            partes_resumen.append(f"{total_no_encontrados} no encontrado{'s' if total_no_encontrados > 1 else ''}")

        resumen_texto = ", ".join(partes_resumen) if partes_resumen else "No se detectaron productos en el dictado."
        mensaje = f"He procesado tu dictado: {resumen_texto}."

        # Construir mensaje de voz natural
        estado_conv_siguiente = "ESPERANDO_PRODUCTOS"
        if total_multiples > 0:
            estado_conv_siguiente = "DESAMBIGUAR_PRODUCTO"
            primer_multiple = next((it for it in items_interpretados if it.estado == "multiple"), None)
            opc_nombres = " o ".join([op.nombre for op in (primer_multiple.opciones[:2] if primer_multiple else [])])
            mensaje_voz = f"Para {primer_multiple.termino_original if primer_multiple else 'el producto'} encontré opciones: {opc_nombres}. ¿Cuál prefieres?"
        elif total_exactos == 1 and len(items_interpretados) == 1:
            it = items_interpretados[0]
            emp_nombre = "cajas" if it.tipo_empaque == "caja" else "unidades"
            mensaje_voz = f"Agregado {it.cantidad} {emp_nombre} de {it.producto.nombre if it.producto else 'producto'}. ¿Deseas agregar más productos o finalizar el pedido?"
        elif total_exactos > 1:
            mensaje_voz = f"Agregados {total_exactos} productos al pedido. ¿Deseas agregar más productos o finalizar?"
        elif total_no_encontrados > 0:
            mensaje_voz = f"No encontré el producto solicitado en el catálogo. ¿Podrías indicarme el nombre o código de otra forma?"
        else:
            mensaje_voz = "No pude entender los productos. Por favor repítemelos con su cantidad."

        return DictadoInterpretadoOutput(
            cliente_detectado_id=cliente_detectado_id or (cliente.id if cliente else None),
            cliente_detectado_nombre=cliente_detectado_nombre or (cliente.alias or cliente.nombre if cliente else None),
            items=items_interpretados,
            mensaje_asistente=mensaje,
            mensaje_voz=mensaje_voz,
            estado_conversacion=estado_conv_siguiente,
            clientes_candidatos=clientes_candidatos_dto,
        )

import re
import unicodedata
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Cliente, Producto
from app.schemas.dto import (
    DictadoItemInterpretado,
    DictadoInterpretadoOutput,
    DictadoProductoMatch,
)
from app.services.pricing import customer_product_box_price, customer_product_price

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
    def detectar_cliente(cls, texto_normalizado: str, db: Session) -> tuple[Cliente | None, str]:
        """
        Intenta detectar si el dictado contiene una mención de cliente:
        Ej: "generame un pedido a nombre de minimarket san jorge los siguientes productos..."
        Retorna (Cliente encontrado o None, texto restante sin el prefijo del cliente).
        """
        patrones = [
            r"(?:generame|genera|crear|haz|hacer)?\s*(?:un\s+)?pedido\s+(?:a\s+nombre\s+de|para\s+el\s+cliente|para\s+cliente|para)\s+([a-zA-Z0-9\s\.\-]+?)(?:\s+(?:los\s+siguientes|con\s+los|y\s+los|productos|con|que\s+lleve|:)|$)",
            r"(?:a\s+nombre\s+de|cliente)\s+([a-zA-Z0-9\s\.\-]+?)(?:\s+(?:los\s+siguientes|con\s+los|y\s+los|productos|con|que\s+lleve|:)|$)",
        ]

        texto_restante = texto_normalizado
        candidato_nombre = ""

        for patron in patrones:
            match = re.search(patron, texto_normalizado)
            if match:
                candidato_nombre = match.group(1).strip()
                # Recortar el prefijo del cliente del texto del dictado
                texto_restante = texto_normalizado[match.end():].strip()
                break

        if not candidato_nombre or len(candidato_nombre) < 2:
            return None, texto_normalizado

        # Buscar cliente en base de datos por alias, nombre o rut
        clientes_activos = list(
            db.scalars(
                select(Cliente)
                .options(selectinload(Cliente.direcciones))
                .where(Cliente.activo.is_(True), Cliente.eliminado_at.is_(None))
            )
        )

        cand_norm = normalizar_texto(candidato_nombre)
        cand_tokens = set(cand_norm.split())

        mejor_cliente = None
        mejor_score = 0.0

        for c in clientes_activos:
            score = 0.0
            alias_norm = normalizar_texto(c.alias or "")
            nombre_norm = normalizar_texto(c.nombre or "")
            rut_norm = normalizar_texto(c.rut or "").replace("-", "").replace(".", "")

            if cand_norm in alias_norm or alias_norm in cand_norm:
                score = max(score, 90.0)
            if cand_norm in nombre_norm or nombre_norm in cand_norm:
                score = max(score, 85.0)
            if cand_norm == rut_norm or cand_norm in rut_norm:
                score = max(score, 95.0)

            # Coincidencia por tokens
            alias_tokens = set(alias_norm.split())
            if cand_tokens and alias_tokens:
                comunes = cand_tokens.intersection(alias_tokens)
                if comunes:
                    pct = (len(comunes) / len(cand_tokens)) * 80.0
                    score = max(score, pct)

            if score > mejor_score and score >= 60.0:
                mejor_score = score
                mejor_cliente = c

        return mejor_cliente, texto_restante if mejor_cliente else texto_normalizado

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
    def extraer_cantidad_y_empaque(cls, frase: str) -> tuple[int, str, str]:
        """
        Extrae la cantidad numérica y el tipo de empaque ('unidad' o 'caja').
        Prioriza pares <cantidad> <empaque> para no confundir números del nombre del producto
        (ej: 'Pall Mall Azul 20 2 cartones', 'Bolsa 35x45 5 unidades').
        Retorna (cantidad, tipo_empaque, termino_limpio_para_buscar).
        """
        texto_norm = normalizar_texto(frase)
        if not texto_norm:
            return 1, "unidad", ""

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

        # Limpiar la frase de la cantidad/empaque extraído
        if sub_eliminado:
            texto_limpio = texto_norm.replace(sub_eliminado, " ", 1)
        else:
            texto_limpio = texto_norm

        tokens = texto_limpio.split()
        tokens_finales = [t for t in tokens if t not in STOPWORDS]
        termino_final = " ".join(tokens_finales).strip()

        return max(1, cantidad), tipo_empaque, termino_final

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
    ) -> DictadoInterpretadoOutput:
        """
        Orquesta la interpretación de voz/texto para armado de pedidos:
        - Detecta cliente si viene en la frase.
        - Segmenta y procesa cada producto dictado con cantidad y unidad/caja.
        - Resuelve coincidencias en catálogo o desambiguación.
        """
        cliente: Cliente | None = None
        if cliente_id:
            cliente = db.get(Cliente, cliente_id)

        texto_trabajo = texto.strip()

        # Si no venía cliente seleccionado, intentar detectarlo del dictado
        cliente_detectado_id = None
        cliente_detectado_nombre = None
        if not cliente:
            cliente_detectado, texto_restante = cls.detectar_cliente(texto_trabajo, db)
            if cliente_detectado:
                cliente = cliente_detectado
                cliente_detectado_id = cliente.id
                cliente_detectado_nombre = cliente.alias or cliente.nombre or cliente.rut
                texto_trabajo = texto_restante

        # Obtener todos los productos activos de la empresa para matching
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
            cant, empaque, termino = cls.extraer_cantidad_y_empaque(frase)
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
                )
            )

        # Generar mensaje explicativo del asistente
        partes_resumen = []
        if total_exactos > 0:
            partes_resumen.append(f"{total_exactos} producto{'s' if total_exactos > 1 else ''} agregado{'s' if total_exactos > 1 else ''}")
        if total_multiples > 0:
            partes_resumen.append(f"{total_multiples} con opciones para elegir")
        if total_no_encontrados > 0:
            partes_resumen.append(f"{total_no_encontrados} no encontrado{'s' if total_no_encontrados > 1 else ''}")

        resumen_texto = ", ".join(partes_resumen) if partes_resumen else "No se detectaron productos en el dictado."
        mensaje = f"He procesado tu dictado: {resumen_texto}."

        return DictadoInterpretadoOutput(
            cliente_detectado_id=cliente_detectado_id or (cliente.id if cliente else None),
            cliente_detectado_nombre=cliente_detectado_nombre or (cliente.alias or cliente.nombre if cliente else None),
            items=items_interpretados,
            mensaje_asistente=mensaje,
        )

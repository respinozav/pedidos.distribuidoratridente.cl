"""Generación del PDF público del catálogo (categorías visibles + productos activos)."""

import base64
import html
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Categoria, Producto

LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo_tridente.png"
PRODUCTS_PER_PAGE = 9
PRODUCTS_PER_ROW = 3
BRAND_NAVY = colors.HexColor("#172B4D")
BRAND_GRAY = colors.HexColor("#667085")
COVER_BACKGROUND = colors.HexColor("#0B1F3A")
COVER_FOOTER_MUTED = colors.HexColor("#7F92B0")
BRAND_GOLD = colors.HexColor("#D4AF37")
BRAND_GOLD_SOFT = colors.HexColor("#E3C878")
CARD_BORDER_COLOR = colors.HexColor("#D9E2EC")
CATEGORY_LINE_COLOR = colors.Color(CARD_BORDER_COLOR.red, CARD_BORDER_COLOR.green, CARD_BORDER_COLOR.blue, alpha=0.55)
CATALOG_URL = "https://www.distribuidoratridente.cl"


class _NumberedCanvas(pdf_canvas.Canvas):
    """Canvas que agrega 'Pagina X de Y' una vez que se conoce el total de paginas."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []
        self._generated_at = datetime.now().strftime("%d-%m-%Y %H:%M")

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(total_pages)
            super().showPage()
        super().save()

    def _draw_page_number(self, total_pages: int) -> None:
        width, _ = A4
        is_cover = self._pageNumber == 1
        self.setFont("Helvetica", 8)
        self.setFillColor(COVER_FOOTER_MUTED if is_cover else BRAND_GRAY)
        self.drawRightString(width - 18 * mm, 15 * mm, f"Actualizado el {self._generated_at}")
        self.drawRightString(width - 18 * mm, 10 * mm, f"Pagina {self._pageNumber} de {total_pages}")


def _cover_background(canvas_obj: pdf_canvas.Canvas, _document: SimpleDocTemplate) -> None:
    width, height = A4
    canvas_obj.saveState()
    canvas_obj.setFillColor(COVER_BACKGROUND)
    canvas_obj.rect(0, 0, width, height, fill=1, stroke=0)
    canvas_obj.restoreState()


def _watermark(canvas_obj: pdf_canvas.Canvas, _document: SimpleDocTemplate) -> None:
    if not LOGO_PATH.is_file():
        return
    width, height = A4
    size = 230 * mm
    canvas_obj.saveState()
    canvas_obj.setFillAlpha(0.07)
    canvas_obj.drawImage(
        str(LOGO_PATH),
        (width - size) / 2,
        (height - size) / 2,
        width=size,
        height=size,
        mask="auto",
        preserveAspectRatio=True,
        anchor="c",
    )
    canvas_obj.restoreState()


def _chunk(items: list, size: int) -> list[list]:
    return [items[index : index + size] for index in range(0, len(items), size)]


class _RoundedCard(Table):
    """Table que dibuja un fondo/borde con esquinas redondeadas detras de su contenido."""

    def __init__(self, *args, radius: float = 8, border_color=None, fill_color=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.radius = radius
        self.border_color = border_color
        self.fill_color = fill_color

    def draw(self) -> None:
        canvas_obj = self.canv
        canvas_obj.saveState()
        if self.border_color:
            canvas_obj.setStrokeColor(self.border_color)
        if self.fill_color:
            canvas_obj.setFillColor(self.fill_color)
        canvas_obj.roundRect(
            0,
            0,
            self._width,
            self._height,
            self.radius,
            stroke=1 if self.border_color else 0,
            fill=1 if self.fill_color else 0,
        )
        canvas_obj.restoreState()
        super().draw()


def _small_caps_markup(text: str, big_size: float, small_size: float) -> str:
    """Simula versalitas: primera letra de cada palabra mas grande, el resto mas pequeno."""
    pieces = []
    for word in text.split(" "):
        if not word:
            continue
        first, rest = html.escape(word[0].upper()), html.escape(word[1:].upper())
        piece = f'<font size="{big_size}">{first}</font>'
        if rest:
            piece += f'<font size="{small_size}">{rest}</font>'
        pieces.append(piece)
    return " ".join(pieces)


def _optimized_image_bytes(raw_bytes: bytes, target_size: int = 260, quality: int = 62) -> bytes:
    with PILImage.open(BytesIO(raw_bytes)) as image:
        image = image.convert("RGB")
        side = min(image.size)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((target_size, target_size), PILImage.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()


def _product_card(product: Producto, styles) -> Table:
    image_flowable: Flowable | None = None
    if product.imagen_url:
        try:
            image_bytes = base64.b64decode(product.imagen_url)
            optimized_bytes = _optimized_image_bytes(image_bytes)
            image_flowable = Image(BytesIO(optimized_bytes), width=30 * mm, height=30 * mm, kind="proportional")
        except (ValueError, OSError):
            image_flowable = None
    if image_flowable is None:
        placeholder = Table([[Paragraph("Sin imagen", styles["CardPlaceholder"])]], colWidths=[30 * mm], rowHeights=[30 * mm])
        placeholder.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7FB")),
                ]
            )
        )
        image_flowable = placeholder
    name = Paragraph(html.escape(product.nombre), styles["CardName"])
    code = Paragraph(f"COD {html.escape(product.codigo)}", styles["CardCode"])
    card = _RoundedCard(
        [[image_flowable], [Spacer(1, 2 * mm)], [name], [Spacer(1, 1 * mm)], [code]],
        colWidths=[52 * mm],
        radius=8,
        border_color=CARD_BORDER_COLOR,
        fill_color=colors.white,
    )
    card.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return card


def _category_title(text: str, styles) -> list:
    return [
        Paragraph(html.escape(text.upper()), styles["CategoryTitle"]),
        HRFlowable(width="100%", thickness=1.4, color=CATEGORY_LINE_COLOR, spaceBefore=2, spaceAfter=6),
    ]


def build_public_catalog_pdf(database: Session) -> bytes:
    categories = list(
        database.scalars(
            select(Categoria)
            .where(
                Categoria.activo.is_(True),
                Categoria.en_catalogo_publico.is_(True),
                Categoria.eliminado_at.is_(None),
            )
            .order_by(Categoria.nombre)
        )
    )

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="Catalogo Distribuidora Tridente",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Heading1"], alignment=TA_CENTER, fontName="Times-Bold", fontSize=24, textColor=BRAND_GOLD, spaceBefore=0))
    styles.add(ParagraphStyle(name="CoverTagline", parent=styles["Normal"], alignment=TA_CENTER, fontSize=11, textColor=BRAND_GOLD_SOFT, spaceBefore=14))
    styles.add(ParagraphStyle(name="CoverWebsite", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=11, textColor=BRAND_GOLD, spaceBefore=8))
    styles.add(ParagraphStyle(name="CategoryTitle", parent=styles["Heading2"], alignment=TA_CENTER, fontName="Times-Bold", fontSize=32, leading=36, textColor=BRAND_GOLD, spaceAfter=4))
    styles.add(ParagraphStyle(name="CardName", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=10, textColor=BRAND_NAVY, leading=12))
    styles.add(ParagraphStyle(name="CardCode", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, textColor=BRAND_GRAY, leading=10))
    styles.add(ParagraphStyle(name="CardPlaceholder", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, textColor=BRAND_GRAY))

    story: list = []

    story.append(Spacer(1, 30 * mm))
    if LOGO_PATH.is_file():
        story.append(Image(str(LOGO_PATH), width=130 * mm, height=92 * mm, kind="proportional"))
        story.append(Spacer(1, 16 * mm))
    story.append(Paragraph(_small_caps_markup("Distribuidora Tridente", 30, 20), styles["CoverTitle"]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Calidad, variedad y confianza en cada pedido.", styles["CoverTagline"]))
    story.append(Paragraph(CATALOG_URL, styles["CoverWebsite"]))
    story.append(PageBreak())

    for category in categories:
        products = list(
            database.scalars(
                select(Producto)
                .where(
                    Producto.categoria_id == category.id,
                    Producto.activo.is_(True),
                    Producto.eliminado_at.is_(None),
                )
                .order_by(Producto.nombre)
            )
        )
        if not products:
            continue
        for chunk in _chunk(products, PRODUCTS_PER_PAGE):
            story.extend(_category_title(category.nombre, styles))
            story.append(Spacer(1, 5 * mm))
            rows = _chunk(chunk, PRODUCTS_PER_ROW)
            table_rows = [[_product_card(product, styles) for product in row] for row in rows]
            for row in table_rows:
                while len(row) < PRODUCTS_PER_ROW:
                    row.append("")
            grid = Table(table_rows, colWidths=[58 * mm, 58 * mm, 58 * mm], hAlign="CENTER")
            grid.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(grid)
            story.append(PageBreak())

    while story and isinstance(story[-1], PageBreak):
        story.pop()

    document.build(story, onFirstPage=_cover_background, onLaterPages=_watermark, canvasmaker=_NumberedCanvas)
    return output.getvalue()

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.catalog import (
    _CATALOG_CACHE,
    _FULL_CATALOG_CACHE,
    build_full_catalog_pdf,
    build_public_catalog_pdf,
    invalidate_catalog_cache,
)


class FakeCatalogSession:
    def __init__(self, categories, products):
        self.categories = categories
        self.products = products

    def scalars(self, statement):
        statement_str = str(statement).lower()
        # If querying categories
        if "categorias" in statement_str:
            # Check if filtering by en_catalogo_publico
            if "en_catalogo_publico" in statement_str:
                return [c for c in self.categories if getattr(c, "activo", True) and getattr(c, "en_catalogo_publico", True)]
            return [c for c in self.categories if getattr(c, "activo", True)]
        # If querying products
        if "productos" in statement_str:
            return [p for p in self.products if getattr(p, "activo", True)]
        return []


def test_build_full_catalog_pdf_returns_valid_pdf():
    cat_private = SimpleNamespace(
        id=uuid4(),
        nombre="Licores Premium",
        activo=True,
        eliminado_at=None,
        en_catalogo_publico=False,
    )
    cat_public = SimpleNamespace(
        id=uuid4(),
        nombre="Bebidas",
        activo=True,
        eliminado_at=None,
        en_catalogo_publico=True,
    )
    prod1 = SimpleNamespace(
        id=uuid4(),
        categoria_id=cat_private.id,
        nombre="Whisky Reserva 12 Años",
        codigo="WH-001",
        precio=Decimal("29990"),
        imagen_url=None,
        activo=True,
        eliminado_at=None,
    )
    prod2 = SimpleNamespace(
        id=uuid4(),
        categoria_id=cat_public.id,
        nombre="Jugo Naranja 1L",
        codigo="JG-001",
        precio=Decimal("1500"),
        imagen_url=None,
        activo=True,
        eliminado_at=None,
    )

    session = FakeCatalogSession(
        categories=[cat_private, cat_public],
        products=[prod1, prod2],
    )

    invalidate_catalog_cache()
    pdf_bytes = build_full_catalog_pdf(session, force_refresh=True)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_build_public_vs_full_catalog_cache_and_invalidation():
    cat = SimpleNamespace(
        id=uuid4(),
        nombre="Test Category",
        activo=True,
        eliminado_at=None,
        en_catalogo_publico=True,
    )
    prod = SimpleNamespace(
        id=uuid4(),
        categoria_id=cat.id,
        nombre="Test Product",
        codigo="TP-001",
        precio=Decimal("5000"),
        imagen_url=None,
        activo=True,
        eliminado_at=None,
    )
    session = FakeCatalogSession(categories=[cat], products=[prod])

    invalidate_catalog_cache()
    assert _CATALOG_CACHE["content"] is None
    assert _FULL_CATALOG_CACHE["content"] is None

    pdf_public = build_public_catalog_pdf(session)
    assert _CATALOG_CACHE["content"] is not None
    assert _FULL_CATALOG_CACHE["content"] is None

    pdf_full = build_full_catalog_pdf(session)
    assert _FULL_CATALOG_CACHE["content"] is not None

    invalidate_catalog_cache()
    assert _CATALOG_CACHE["content"] is None
    assert _FULL_CATALOG_CACHE["content"] is None

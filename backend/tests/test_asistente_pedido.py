import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.entities import Categoria, Cliente, Direccion, Producto, Usuario
from app.schemas.dto import AdminOrderCreateInput, DictadoInterpretadoInput, OrderLineInput
from app.services.asistente_pedido_service import AsistentePedidoService, normalizar_texto


def test_normalizar_texto_y_cantidades():
    assert normalizar_texto("¡Bolsa Camiseta 35x45 (Paq x100)!") == "bolsa camiseta 35x45 paq x100"
    
    cant1, emp1, term1 = AsistentePedidoService.extraer_cantidad_y_empaque("BOLSA CAMISETA 35X45 (PAQ X100) 5 unidades")
    assert cant1 == 5
    assert emp1 == "unidad"
    assert "bolsa camiseta 35x45" in term1

    cant2, emp2, term2 = AsistentePedidoService.extraer_cantidad_y_empaque("PALL MALL AZUL 20 BLANDO 2 cartones")
    assert cant2 == 2
    assert emp2 == "caja"
    assert "pall mall azul 20 blando" in term2

    cant3, emp3, term3 = AsistentePedidoService.extraer_cantidad_y_empaque("KENT ACTRON un carton")
    assert cant3 == 1
    assert emp3 == "caja"
    assert "kent actron" in term3


def test_segmentar_clausulas_compuestas():
    frase = "Bolsa camiseta 35x45 5 unidades, Pall Mall Azul 20 blando 2 cartones y Kent Actron 1 carton"
    clausulas = AsistentePedidoService.segmentar_clausulas(frase)
    assert len(clausulas) == 3
    assert "Bolsa camiseta 35x45 5 unidades" in clausulas[0]
    assert "Pall Mall Azul 20 blando 2 cartones" in clausulas[1]
    assert "Kent Actron 1 carton" in clausulas[2]


def test_buscar_producto_exacto_y_multiple():
    cat = Categoria(id=uuid4(), nombre="Cigarrillos", porcentaje=Decimal("0.00"), usa_porcentaje_cliente=False)
    p1 = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="PM-AZUL-20",
        nombre="PALL MALL AZUL 20 BLANDO",
        precio=Decimal("3500.00"),
        cantidad=100,
        activo=True,
        tiene_caja=True,
        cantidad_caja=10,
        precio_caja=Decimal("35000.00"),
    )
    p2 = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="KENT-ACT",
        nombre="KENT ACTRON",
        precio=Decimal("4200.00"),
        cantidad=50,
        activo=True,
        tiene_caja=True,
        cantidad_caja=10,
        precio_caja=Decimal("42000.00"),
    )
    p3 = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="KENT-B4",
        nombre="KENT BLUE 4",
        precio=Decimal("4200.00"),
        cantidad=40,
        activo=True,
        tiene_caja=True,
        cantidad_caja=10,
        precio_caja=Decimal("42000.00"),
    )
    p_inactivo = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="OLD-PROD",
        nombre="PRODUCTO VIEJO INACTIVO",
        precio=Decimal("1000.00"),
        cantidad=0,
        activo=False,
    )

    productos = [p1, p2, p3]

    # 1. Búsqueda exacta de Pall Mall
    estado1, prod1, opc1 = AsistentePedidoService.buscar_producto_en_catalogo(
        "pall mall azul 20 blando", productos
    )
    assert estado1 == "exacto"
    assert prod1 is not None
    assert prod1.codigo == "PM-AZUL-20"
    assert len(opc1) == 0

    # 2. Búsqueda ambigua: solo "kent" encuentra Kent Actron y Kent Blue 4
    estado2, prod2, opc2 = AsistentePedidoService.buscar_producto_en_catalogo(
        "kent", productos
    )
    assert estado2 == "multiple"
    assert prod2 is None
    assert len(opc2) >= 2
    codigos_opciones = {op.codigo for op in opc2}
    assert "KENT-ACT" in codigos_opciones
    assert "KENT-B4" in codigos_opciones

    # 3. Búsqueda de producto inexistente
    estado3, prod3, opc3 = AsistentePedidoService.buscar_producto_en_catalogo(
        "whisky chivas 18 anos", productos
    )
    assert estado3 == "no_encontrado"
    assert prod3 is None
    assert len(opc3) == 0


def test_interpretar_dictado_completo():
    db = MagicMock()
    cat = Categoria(id=uuid4(), nombre="General", porcentaje=Decimal("0.00"), usa_porcentaje_cliente=False)
    p_bolsa = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="BC-35X45",
        nombre="BOLSA CAMISETA 35X45 (PAQ X100)",
        precio=Decimal("1200.00"),
        cantidad=500,
        activo=True,
    )
    p_kent = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="KENT-ACT",
        nombre="KENT ACTRON",
        precio=Decimal("4200.00"),
        cantidad=100,
        activo=True,
    )
    db.scalars.return_value = [p_bolsa, p_kent]
    db.get.return_value = None

    texto = "BOLSA CAMISETA 35X45 (PAQ X100) 5 unidades, KENT ACTRON 2 unidades"
    resultado = AsistentePedidoService.interpretar_dictado(texto, None, db)

    assert len(resultado.items) == 2
    assert resultado.items[0].cantidad == 5
    assert resultado.items[0].estado == "exacto"
    assert resultado.items[0].producto.codigo == "BC-35X45"

    assert resultado.items[1].cantidad == 2
    assert resultado.items[1].estado == "exacto"
    assert resultado.items[1].producto.codigo == "KENT-ACT"
    assert "2 productos agregados" in resultado.mensaje_asistente


def test_asistente_detectar_cliente_y_productos_compuestos():
    db = MagicMock()
    cat = Categoria(id=uuid4(), nombre="Cigarrillos", porcentaje=Decimal("0.00"), usa_porcentaje_cliente=False)
    p_bolsa = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="BC-35X45",
        nombre="BOLSA CAMISETA 35X45 (PAQ X100)",
        precio=Decimal("1200.00"),
        cantidad=500,
        activo=True,
    )
    p_pm = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="PM-AZUL-20",
        nombre="PALL MALL AZUL 20 BLANDO",
        precio=Decimal("3500.00"),
        cantidad=100,
        activo=True,
    )
    p_kent = Producto(
        id=uuid4(),
        categoria=cat,
        codigo="KENT-ACT",
        nombre="KENT ACTRON",
        precio=Decimal("4200.00"),
        cantidad=100,
        activo=True,
    )
    cliente_prueba = Cliente(
        id=uuid4(),
        nombre="Botilleria Los Olivos SPA",
        alias="Botilleria Los Olivos",
        rut="76123456-7",
        activo=True,
        porcentaje=Decimal("0.00"),
    )

    def mock_scalars(query):
        # Si la consulta es de clientes o de productos
        str_q = str(query)
        if "clientes" in str_q:
            return [cliente_prueba]
        return [p_bolsa, p_pm, p_kent]

    db.scalars.side_effect = mock_scalars
    db.get.return_value = None

    texto = "generame un pedido a nombre de Botilleria Los Olivos los siguientes productos BOLSA CAMISETA 35X45 (PAQ X100) 5 unidades, PALL MALL AZUL 20 BLANDO 2 cartones y KENT ACTRON 1 carton"
    resultado = AsistentePedidoService.interpretar_dictado(texto, None, db)

    assert resultado.cliente_detectado_id == cliente_prueba.id
    assert len(resultado.items) == 3
    assert resultado.items[0].cantidad == 5
    assert resultado.items[0].producto.codigo == "BC-35X45"
    assert resultado.items[1].cantidad == 2
    assert resultado.items[1].tipo_empaque == "caja"
    assert resultado.items[1].producto.codigo == "PM-AZUL-20"
    assert resultado.items[2].cantidad == 1
    assert resultado.items[2].tipo_empaque == "caja"
    assert resultado.items[2].producto.codigo == "KENT-ACT"


if __name__ == "__main__":
    test_normalizar_texto_y_cantidades()
    print("✓ test_normalizar_texto_y_cantidades PASSED")
    test_segmentar_clausulas_compuestas()
    print("✓ test_segmentar_clausulas_compuestas PASSED")
    test_buscar_producto_exacto_y_multiple()
    print("✓ test_buscar_producto_exacto_y_multiple PASSED")
    test_interpretar_dictado_completo()
    print("✓ test_interpretar_dictado_completo PASSED")
    test_asistente_detectar_cliente_y_productos_compuestos()
    print("✓ test_asistente_detectar_cliente_y_productos_compuestos PASSED")
    print(">>> ALL ASISTENTE PEDIDO TESTS PASSED SUCCESSFULLY! <<<")

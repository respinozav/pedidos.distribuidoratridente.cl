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


def test_comandos_de_voz():
    db = MagicMock()
    # 1. Comando finalizar
    r_fin = AsistentePedidoService.interpretar_dictado("finalizar pedido", None, db)
    assert r_fin.comando_detectado == "finalizar"
    assert r_fin.estado_conversacion == "CONFIRMACION_FINAL"
    assert "¿Deseas confirmar" in r_fin.mensaje_voz

    # 2. Comando confirmar
    r_conf = AsistentePedidoService.interpretar_dictado("si confirmar", None, db)
    assert r_conf.comando_detectado == "confirmar"
    assert r_conf.estado_conversacion == "CONFIRMANDO"

    # 3. Comando eliminar
    r_elim = AsistentePedidoService.interpretar_dictado("eliminar bolsa camiseta", None, db)
    assert r_elim.comando_detectado == "eliminar"
    assert r_elim.parametro_comando == "bolsa camiseta"
    assert "Eliminado bolsa camiseta" in r_elim.mensaje_voz

    # 4. Comando vaciar
    r_vac = AsistentePedidoService.interpretar_dictado("vaciar pedido", None, db)
    assert r_vac.comando_detectado == "vaciar"


def test_producto_sin_cantidad_solicita_cantidad():
    db = MagicMock()
    cat = Categoria(id=uuid4(), nombre="General", porcentaje=Decimal("0.00"), usa_porcentaje_cliente=False)
    p = Producto(id=uuid4(), categoria=cat, codigo="VASO-500", nombre="VASO TRANSPARENTE 500CC", precio=Decimal("1500.00"), cantidad=100, activo=True)
    
    def mock_sc(query):
        if "clientes" in str(query):
            return []
        return [p]
        
    db.scalars.side_effect = mock_sc
    db.get.return_value = None

    # Solo dicta el nombre del producto sin cantidad
    resultado = AsistentePedidoService.interpretar_dictado("VASO TRANSPARENTE 500CC", None, db)
    assert resultado.estado_conversacion == "ESPERANDO_CANTIDAD"
    assert resultado.producto_pendiente_cantidad is not None
    assert resultado.producto_pendiente_cantidad.codigo == "VASO-500"
    assert "Cuántas unidades o paquetes deseas agregar" in resultado.mensaje_voz


def test_busqueda_cliente_afinada_tokens_y_tildes():
    db = MagicMock()
    c1 = Cliente(
        id=uuid4(),
        nombre="Comercial Pérez y Compañía SpA",
        alias="Almacén Don Pérez",
        rut="76.123.456-7",
        celular="+56991234567",
        activo=True,
    )
    c2 = Cliente(
        id=uuid4(),
        nombre="Sociedad Minimarket San Jorge Limitada",
        alias="Minimarket San Jorge",
        rut="77.987.654-K",
        celular="+56987654321",
        activo=True,
    )

    db.scalars.return_value = [c1, c2]

    # 1. Búsqueda sin tilde ("perez" vs "Pérez")
    cli1, _, _ = AsistentePedidoService.detectar_candidatos_cliente("perez", db)
    assert cli1 is not None
    assert cli1.id == c1.id

    # 2. Búsqueda con orden invertido y con relleno ("San Jorge Almacen" o "San Jorge")
    cli2, _, _ = AsistentePedidoService.detectar_candidatos_cliente("pedido para San Jorge", db)
    assert cli2 is not None
    assert cli2.id == c2.id

    # 3. Búsqueda por RUT sin puntos ni guiones ("76123456")
    cli3, _, _ = AsistentePedidoService.detectar_candidatos_cliente("76123456", db)
    assert cli3 is not None
    assert cli3.id == c1.id


def test_cliente_prueba_sin_falsos_positivos_alias_nulo():
    db = MagicMock()
    # Simular clientes reales de la base de datos sin alias
    c1 = Cliente(id=uuid4(), nombre="Sergio Cortes", alias=None, rut="11111111-1", activo=True)
    c2 = Cliente(id=uuid4(), nombre="Espiga de oro", alias=None, rut="22222222-2", activo=True)
    c3 = Cliente(id=uuid4(), nombre="WH Handler spa", alias=None, rut="33333333-3", activo=True)
    c4 = Cliente(id=uuid4(), nombre="Sociedad Comercial Amma LTDA", alias=None, rut="44444444-4", activo=True)
    cp = Cliente(id=uuid4(), nombre="Cliente Prueba", alias="Cliente Prueba", rut="99999999-9", activo=True)

    db.scalars.return_value = [c1, c2, c3, c4, cp]

    # Al buscar "Cliente Prueba", no debe traer [c1, c2, c3, c4], debe detectar inmediatamente a Cliente Prueba
    cli, rest, cands = AsistentePedidoService.detectar_candidatos_cliente("Cliente Prueba", db)
    assert cli is not None
    assert cli.id == cp.id
    assert len(cands) == 0

    # También con frase con prefijo "pedido para Cliente Prueba"
    cli_pref, _, _ = AsistentePedidoService.detectar_candidatos_cliente("pedido para Cliente Prueba", db)
    assert cli_pref is not None
    assert cli_pref.id == cp.id


def test_detectar_categoria_cigarros_y_lee_marcas():
    """Al dictar 'cigarros', el agente debe detectar la categoría Cigarrillos y leer sus marcas disponibles."""
    db = MagicMock()
    cat_cig = Categoria(id=uuid4(), nombre="Cigarrillos", activo=True)
    p1 = Producto(id=uuid4(), codigo="PM-1", nombre="PALL MALL AZUL 20 BLANDO", categoria=cat_cig, categoria_id=cat_cig.id, activo=True, precio=Decimal("3500"))
    p2 = Producto(id=uuid4(), codigo="PM-2", nombre="PALL MALL ROJO 20", categoria=cat_cig, categoria_id=cat_cig.id, activo=True, precio=Decimal("3500"))
    p3 = Producto(id=uuid4(), codigo="K-1", nombre="KENT ACTRON", categoria=cat_cig, categoria_id=cat_cig.id, activo=True, precio=Decimal("4200"))
    p4 = Producto(id=uuid4(), codigo="LS-1", nombre="LUCKY STRIKE CLICK", categoria=cat_cig, categoria_id=cat_cig.id, activo=True, precio=Decimal("4000"))

    db.scalars.side_effect = lambda q: [cat_cig] if "categorias" in str(q) else [p1, p2, p3, p4]
    db.get.return_value = None

    # 1. Dictado 'cigarros'
    res = AsistentePedidoService.interpretar_dictado("cigarros", None, db)
    assert res.estado_conversacion == "EXPLORANDO_CATEGORIA"
    assert res.categoria_detectada == "Cigarrillos"
    assert "Pall Mall" in res.marcas_categoria
    assert "Kent" in res.marcas_categoria
    assert "Lucky Strike" in res.marcas_categoria
    assert "¿Qué cigarros buscas?" in res.mensaje_voz
    assert "Pall Mall, Kent y Lucky Strike" in res.mensaje_voz

    # 2. Dictado de categoría Bolsas
    cat_bol = Categoria(id=uuid4(), nombre="Bolsas", activo=True)
    pb1 = Producto(id=uuid4(), codigo="B-1", nombre="BOLSA CAMISETA 35X45 (PAQ X100)", categoria=cat_bol, categoria_id=cat_bol.id, activo=True, precio=Decimal("1200"))
    pb2 = Producto(id=uuid4(), codigo="B-2", nombre="BOLSA TACO TRANSPARENTE", categoria=cat_bol, categoria_id=cat_bol.id, activo=True, precio=Decimal("900"))

    db.scalars.side_effect = lambda q: [cat_bol] if "categorias" in str(q) else [pb1, pb2]
    res_b = AsistentePedidoService.interpretar_dictado("bolsas", None, db)
    assert res_b.estado_conversacion == "EXPLORANDO_CATEGORIA"
    assert res_b.categoria_detectada == "Bolsas"
    assert "Bolsa Camiseta" in res_b.marcas_categoria
    assert "Bolsa Taco" in res_b.marcas_categoria
    assert "bolsas necesitas?" in res_b.mensaje_voz


def test_modelo_numerico_no_se_confunde_con_cantidad():
    # 1. Extracción de cantidades y términos con números de modelo (ej: 2025, 2016, 2032)
    c1, e1, t1, exp1 = AsistentePedidoService.extraer_cantidad_y_empaque_detallado("pilas duracell 2025")
    assert c1 == 1
    assert "2025" in t1
    assert exp1 is False

    c2, e2, t2, exp2 = AsistentePedidoService.extraer_cantidad_y_empaque_detallado("la duracell 2025")
    assert c2 == 1
    assert "2025" in t2
    assert exp2 is False

    c3, e3, t3, exp3 = AsistentePedidoService.extraer_cantidad_y_empaque_detallado("2 pilas duracell 2025")
    assert c3 == 2
    assert "2025" in t3
    assert exp3 is True

    c4, e4, t4, exp4 = AsistentePedidoService.extraer_cantidad_y_empaque_detallado("kent actron 3")
    assert c4 == 3
    assert "kent actron" in t4
    assert exp4 is True

    c5, e5, t5, exp5 = AsistentePedidoService.extraer_cantidad_y_empaque_detallado("3 kent actron")
    assert c5 == 3
    assert "kent actron" in t5
    assert exp5 is True

    # 2. Búsqueda exacta de producto con modelo numérico
    cat = Categoria(id=uuid4(), nombre="Abarrotes", activo=True)
    p2016 = Producto(id=uuid4(), codigo="PD2016", nombre="Pilas Duracell 2016", categoria=cat, categoria_id=cat.id, activo=True, precio=Decimal("3410"))
    p2025 = Producto(id=uuid4(), codigo="PD2025", nombre="Pilas Duracell 2025", categoria=cat, categoria_id=cat.id, activo=True, precio=Decimal("3410"))
    p2032 = Producto(id=uuid4(), codigo="PD2032", nombre="Pilas Duracell 2032", categoria=cat, categoria_id=cat.id, activo=True, precio=Decimal("3410"))
    p9v = Producto(id=uuid4(), codigo="PD9V", nombre="Pilas Duracell 9 V (bateria)", categoria=cat, categoria_id=cat.id, activo=True, precio=Decimal("3611"))
    pa13 = Producto(id=uuid4(), codigo="PDA13", nombre="Pilas Duracell Auditiva 13", categoria=cat, categoria_id=cat.id, activo=True, precio=Decimal("2836"))
    catalogo = [p2016, p2025, p2032, p9v, pa13]

    for consulta in ["pilas duracell 2025", "la duracell 2025", "duracell 2025", "la 2025", "2025"]:
        estado, prod, opciones = AsistentePedidoService.buscar_producto_en_catalogo(consulta, catalogo)
        assert estado == "exacto", f"Fallo para consulta '{consulta}': estado={estado}"
        assert prod is not None
        assert prod.nombre == "Pilas Duracell 2025"
        assert len(opciones) == 0

    # 3. Interpretación de dictado con cantidad y modelo numérico
    db = MagicMock()
    cliente = Cliente(id=uuid4(), nombre="Minimarket Don Pedro", rut="76.111.222-3")
    db.get.return_value = cliente
    db.scalars.side_effect = lambda q: catalogo

    res = AsistentePedidoService.interpretar_dictado("2 pilas duracell 2025", cliente.id, db)
    assert len(res.items) == 1
    it = res.items[0]
    assert it.estado == "exacto"
    assert it.producto.nombre == "Pilas Duracell 2025"
    assert it.cantidad == 2
    assert it.cantidad_explicita is True
    assert "Agregado 2 unidades de Pilas Duracell 2025" in res.mensaje_voz


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
    test_comandos_de_voz()
    print("✓ test_comandos_de_voz PASSED")
    test_producto_sin_cantidad_solicita_cantidad()
    print("✓ test_producto_sin_cantidad_solicita_cantidad PASSED")
    test_busqueda_cliente_afinada_tokens_y_tildes()
    print("✓ test_busqueda_cliente_afinada_tokens_y_tildes PASSED")
    test_cliente_prueba_sin_falsos_positivos_alias_nulo()
    print("✓ test_cliente_prueba_sin_falsos_positivos_alias_nulo PASSED")
    test_detectar_categoria_cigarros_y_lee_marcas()
    print("✓ test_detectar_categoria_cigarros_y_lee_marcas PASSED")
    test_modelo_numerico_no_se_confunde_con_cantidad()
    print("✓ test_modelo_numerico_no_se_confunde_con_cantidad PASSED")
    print(">>> ALL ASISTENTE PEDIDO TESTS PASSED SUCCESSFULLY! <<<")

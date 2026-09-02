from decimal import Decimal, ROUND_HALF_UP

from app.models.entities import Cliente, Producto


def customer_product_price(product: Producto, customer: Cliente) -> Decimal:
    percentage = customer.porcentaje if product.categoria.usa_porcentaje_cliente else product.categoria.porcentaje
    multiplier = Decimal("1") + percentage / Decimal("100")
    return (product.precio * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def customer_product_box_price(product: Producto, customer: Cliente) -> Decimal | None:
    if not product.tiene_caja:
        return None
    
    if product.precio_caja is not None and product.precio_caja > 0:
        base_price = product.precio_caja
    elif product.cantidad_caja is not None and product.cantidad_caja > 0:
        base_price = product.precio * Decimal(str(product.cantidad_caja))
    else:
        return None

    percentage = customer.porcentaje if product.categoria.usa_porcentaje_cliente else product.categoria.porcentaje
    multiplier = Decimal("1") + percentage / Decimal("100")
    return (base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
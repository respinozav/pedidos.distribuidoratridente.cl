from decimal import Decimal, ROUND_HALF_UP

from app.models.entities import Cliente, Producto


def customer_product_price(product: Producto, customer: Cliente) -> Decimal:
    percentage = customer.porcentaje if product.categoria.usa_porcentaje_cliente else product.categoria.porcentaje
    multiplier = Decimal("1") + percentage / Decimal("100")
    return (product.precio * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
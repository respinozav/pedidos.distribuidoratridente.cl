from app.core.database import SessionLocal
from app.models.entities import Cliente, Direccion, Producto
from app.schemas.dto import OrderCreate, OrderLineInput
from app.services.ordering import OrderService
from sqlalchemy import select

s = SessionLocal()
customer = s.scalar(select(Cliente).where(Cliente.correo == 'cliente@cliente.cl'))
address = s.scalar(select(Direccion).where(Direccion.cliente_id == customer.id, Direccion.activo.is_(True)).order_by(Direccion.created_at.asc()))
product = s.scalar(select(Producto).where(Producto.activo.is_(True)).order_by(Producto.created_at.asc()))
payload = OrderCreate(direccion_id=address.id, productos=[OrderLineInput(producto_id=product.id, cantidad=1)])
order = OrderService(s).create(customer.id, payload)
print(order.id)
print(order.estado.nombre)
s.close()

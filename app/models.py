from django.db import models
from django.contrib.auth.models import AbstractUser

class Producto(models.Model):
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'producto'
    
class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='inventarios')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    class Meta:
        db_table = 'inventario'

class Rol(models.Model):
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'rol'

class CustomUser(AbstractUser):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    rol = models.ForeignKey(Rol, on_delete=models.RESTRICT, null=True, blank=True)

    class Meta:
        db_table = 'customuser'
    def __str__(self):
        return f"{self.username} - {self.rol.nombre if self.rol else 'Sin rol'}"

class Venta(models.Model):
    total = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    cliente = models.ForeignKey(
        CustomUser,
        related_name='ventas_como_cliente',
        on_delete=models.CASCADE
    )
    cajero = models.ForeignKey(
        CustomUser,
        related_name='ventas_como_cajero',
        on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'venta'

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalleventas')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('venta', 'producto')
        db_table = 'detalleventa'

class Pedido(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_CAMINO', 'En camino'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE'   # <— valor por defecto
    )
    fecha = models.DateTimeField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    direccion = models.TextField()
    cliente = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='pedidos_cliente')
    repartidor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True,blank=True)

    class Meta:
        db_table = 'pedido'
    def __str__(self):
        cliente = getattr(self.cliente, "username", "¿sin cliente?")
        return f"Pedido #{self.id} · {self.get_estado_display()} · {cliente}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detallepedidos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('pedido', 'producto')

        db_table = 'detallepedido'

class Factura(models.Model):
    fecha = models.DateTimeField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pago = models.CharField(max_length=50)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)

    class Meta:
        db_table = 'factura'

class Reporte(models.Model):
    fecha_generada = models.DateTimeField()
    tipo = models.CharField(max_length=50)
    parametro = models.TextField(null=True, blank=True)
    cajero = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    class Meta:
        db_table = 'reporte'

class Bitacora(models.Model):
    login = models.DateTimeField()
    logout = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IPv4 o IPv6 del dispositivo"
    )
    device = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Ubicación aproximada (p.ej. 'Ciudad, País' o 'lat,lon')"
    )

    class Meta:
        db_table = 'bitacora'

class DetalleBitacora(models.Model):
    bitacora = models.ForeignKey(Bitacora, on_delete=models.CASCADE, related_name='detallebitacoras')
    accion = models.CharField(max_length=100)
    fecha = models.DateTimeField()
    tabla = models.CharField(max_length=50)

    class Meta:
        db_table = 'detallebitacora'

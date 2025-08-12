from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.db.models import F 
from .models import (
    Producto, Inventario, Rol, CustomUser,
    Venta, DetalleVenta, Pedido, DetallePedido,
    Factura, Reporte, Bitacora, DetalleBitacora
)

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields  = ['id', 'nombre']

class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventario
        fields  =['id','producto', 'precio','stock']

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields  = ['id', 'nombre']

#Read:para liststar/detalle 89 c
class CustomUserReadSerializer(serializers.ModelSerializer):
    rol=RolSerializer()
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'rol']
        
#write prar crear/actualizar (rol id+password write-ony))
class CustomUserWriteSerializer(serializers.ModelSerializer):
    rol=serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(),allow_null=True,required=False)
    username = serializers.CharField(
        max_length=150,
        validators=[
            UniqueValidator(
                queryset=CustomUser.objects.all(),
                message="Ya existe un usuario con este nombre de usuario."
            )
        ]
    )
    password=serializers.CharField(write_only=True,required=True,min_length=6)
    class Meta:
        model=CustomUser
        fields=['id','username','password','rol']

    def create(self, validated_data):
        pwd=validated_data.pop('password')
        user=CustomUser(**validated_data)
        user.set_password(pwd)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        pwd=validated_data.pop('password',None)
        for k,v in validated_data.items():
            setattr(instance,k,v)
        if pwd:
            instance.set_password(pwd)
        instance.save()    
        return instance

class VentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = '__all__'

class DetalleVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVenta
        fields = '__all__'

# serializers.py

from rest_framework import serializers
from django.db import transaction
from .models import Pedido, DetallePedido
"""
 [
    {
      "producto": 1,
      "cantidad": 2,
      "precio_unitario": 10.00,
      "subtotal": 20.00
    },
    {
      "producto": 2,
      "cantidad": 3,
      "precio_unitario": 5.00,
      "subtotal": 15.00
    }
  ]
"""
class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']

"""
{
  "fecha": "...",
  "total": 123.45,
  "direccion": "Calle Falsa 123",
  "detallepedidos": [
    {"producto": 1, "cantidad":2, "precio_unitario":10.0, "subtotal":20.0},
    {"producto": 5, "cantidad":1, "precio_unitario":15.0, "subtotal":15.0}
  ]
}

"""
class PedidoSerializer(serializers.ModelSerializer):
    cliente = serializers.HiddenField(default=serializers.CurrentUserDefault())
    detallepedidos = DetallePedidoSerializer(many=True)

    class Meta:
        model = Pedido
        # Incluye el campo anidado
        fields = ['id', 'estado', 'fecha', 'total', 'direccion', 'cliente', 'detallepedidos']
        read_only_fields = ['id', 'cliente', 'estado']

    def create(self, validated_data):
        detalles_data = validated_data.pop('detallepedidos', [])

        with transaction.atomic():
            # 1) Bloqueamos inventarios de todos los productos involucrados
            product_ids = []
            for d in detalles_data:
                p = d['producto']
                pid = p.id if isinstance(p, Producto) else int(p)
                product_ids.append(pid)

            inv_qs = Inventario.objects.select_for_update().filter(producto_id__in=product_ids)
            inv_map = {inv.producto_id: inv for inv in inv_qs}

            # 2) Validaciones: inventario existente y stock suficiente (sumando cantidades por producto)
            missing = set(product_ids) - set(inv_map.keys())
            if missing:
                raise serializers.ValidationError({
                    'detallepedidos': f'No existe inventario para producto(s): {sorted(list(missing))}'
                })

            qty_by_product = {}
            for d in detalles_data:
                pid = d['producto'].id if isinstance(d['producto'], Producto) else int(d['producto'])
                qty_by_product[pid] = qty_by_product.get(pid, 0) + int(d['cantidad'])

            insuficientes = []
            for pid, qty in qty_by_product.items():
                if inv_map[pid].stock < qty:
                    insuficientes.append({
                        'producto': pid,
                        'disponible': inv_map[pid].stock,
                        'solicitado': qty
                    })

            if insuficientes:
                raise serializers.ValidationError({
                    'detallepedidos': 'Stock insuficiente para uno o más productos.',
                    'faltantes': insuficientes
                })

            # 3) Crear Pedido
            pedido = Pedido.objects.create(**validated_data)

            # 4) Construir Detalles (tomamos precio de inventario si no viene)
            detalles = []
            for d in detalles_data:
                pid = d['producto'].id if isinstance(d['producto'], Producto) else int(d['producto'])
                inv = inv_map[pid]
                precio_unitario = d.get('precio_unitario', inv.precio)
                subtotal = d.get('subtotal', precio_unitario * d['cantidad'])

                detalles.append(DetallePedido(
                    pedido=pedido,
                    producto=d['producto'],
                    cantidad=d['cantidad'],
                    precio_unitario=precio_unitario,
                    subtotal=subtotal
                ))

            DetallePedido.objects.bulk_create(detalles)

            # 5) Descontar stock (seguro contra condiciones de carrera)
            for pid, qty in qty_by_product.items():
                Inventario.objects.filter(producto_id=pid).update(stock=F('stock') - qty)

            # (Opcional) recalcular total del pedido en el servidor:
            # pedido.total = sum(d.subtotal for d in pedido.detallepedidos.all())
            # pedido.save(update_fields=['total'])

            return pedido

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class ReporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reporte
        fields = '__all__'

class BitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitacora
        fields = '__all__'

class DetalleBitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleBitacora
        fields = '__all__'

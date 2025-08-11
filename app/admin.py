# admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Producto, Inventario, Rol, CustomUser, Venta,
    DetalleVenta, Pedido, DetallePedido,
    Factura, Reporte, Bitacora, DetalleBitacora
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Datos adicionales', {'fields': ('rol',)}),
    )

@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'login', 'logout', 'ip', 'device')
    list_filter = ('usuario', 'ip', 'device')
    search_fields = ('usuario__username', 'ip', 'device')

@admin.register(DetalleBitacora)
class DetalleBitacoraAdmin(admin.ModelAdmin):
    list_display = ('bitacora', 'accion', 'fecha', 'tabla')
    list_filter = ('accion', 'tabla')
    search_fields = ('bitacora__usuario__username', 'accion', 'tabla')
    
@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')  # Ahora se mostrará "nombre" en lugar de "Rol object (x)"

# Registro simple para el resto de modelos
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "estado", "fecha", "cliente", "total")
    list_filter = ("estado", "fecha")
    search_fields = ("cliente__username", "direccion")
    ordering = ("-fecha",)             # opcional: más recientes primero

@admin.register(Inventario)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id','producto', 'precio','stock')
    
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display =  ('id', 'nombre')
    
admin.site.register(Venta)
admin.site.register(DetalleVenta)

admin.site.register(DetallePedido)
admin.site.register(Factura)
admin.site.register(Reporte)

from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets,status
from  django.utils import timezone


# Create your views here.
# views.py
import logging
logger = logging.getLogger(__name__)

from rest_framework import viewsets
from .models import (
    Producto, Inventario, Rol, CustomUser, Venta,
    DetalleVenta, Pedido, DetallePedido,
    Factura, Reporte, Bitacora, DetalleBitacora
)
from .serializers import (
    ProductoSerializer, InventarioSerializer, RolSerializer,
    CustomUserWriteSerializer,CustomUserReadSerializer, VentaSerializer, DetalleVentaSerializer,
    PedidoSerializer, DetallePedidoSerializer,
    FacturaSerializer, ReporteSerializer,
    BitacoraSerializer, DetalleBitacoraSerializer
)
from .models import Bitacora,DetalleBitacora
#permissions
from .permissions import IsAdmin, IsRepartidor, IsCliente
from rest_framework.permissions import AllowAny, IsAuthenticated
# === Auditoría de acciones en Bitácora ===
from django.utils import timezone

class BitacoraLoggerMixin:
    """
    Mixin para registrar automáticamente acciones del actor (request.user)
    en DetalleBitacora, reusando (o creando) su Bitacora abierta.
    """

    def _current_bitacora(self, request):
        bit = Bitacora.objects.filter(
            usuario=request.user,
            logout__isnull=True
        ).last()
        if bit is None:
            # Abrimos una bitácora mínima para el ACTOR
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None
            device = request.META.get('HTTP_USER_AGENT') or None
            bit = Bitacora.objects.create(
                usuario=request.user,   # ACTOR
                login=timezone.now(),
                ip=ip,
                device=device
            )
        return bit

    def _log(self, request, accion: str, tabla: str):
        bit = self._current_bitacora(request)
        DetalleBitacora.objects.create(
            bitacora=bit,
            accion=accion,
            fecha=timezone.now(),
            tabla=tabla
        )

    def _tabla(self):
        # Usa el nombre de tabla real del modelo (db_table) para consistencia
        try:
            return self.get_queryset().model._meta.db_table
        except Exception:
            return self.__class__.__name__.lower()

    # Hooks para operaciones DRF comunes
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        self._log(request, "LISTAR", self._tabla())
        return resp

    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        self._log(request, "VER_DETALLE", self._tabla())
        return resp

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        self._log(request, "CREAR", self._tabla())
        return resp

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        self._log(request, "EDITAR", self._tabla())
        return resp

    def partial_update(self, request, *args, **kwargs):
        resp = super().partial_update(request, *args, **kwargs)
        self._log(request, "EDITAR_PARCIAL", self._tabla())
        return resp

    def destroy(self, request, *args, **kwargs):
        resp = super().destroy(request, *args, **kwargs)
        self._log(request, "ELIMINAR", self._tabla())
        return resp
# === fin mixin ===
class ProductoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class InventarioViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer

class RolViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer

class CustomUserViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    permission_classes = [IsAdmin,IsAuthenticated]
    @action(
        detail=False,
        methods=['get'],
        url_path='me',
        permission_classes=[IsAuthenticated]   
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    def get_serializer_class(self):
        if self.action in ['create','update','partial_update']:
            return  CustomUserWriteSerializer
        return CustomUserReadSerializer
    
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        try:
            ser.is_valid(raise_exception=True)
        except ValidationError as e:
            safe_data = {**request.data}
            safe_data.pop('password', None)   # nunca loguees passwords
            logger.warning(
                "POST /api/usuarios/ inválido por %s · data=%s · errors=%s",
                request.user, safe_data, e.detail
            )
            raise
        user = ser.save()
        logger.info("Usuario creado id=%s username=%s por=%s",
                    user.id, user.username, request.user)
        #Registro de DetalleBitacora
        bit=Bitacora.objects.filter(
            usuario=request.user,
            logout__isnull=True
        ).last()
        if bit is None:
            #opciional no perder el rastro daque qel acton no eteng hbitacora abierta
            xff=request.META.get('HTTP_X_FORWARDED_FOR')
            ip=(xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None
            device=request.META.get('HTTP_USER_AGENT') or None
            bit=Bitacora.objects.create(
                usuario=user,
                login= timezone.now(),
                ip=ip,
                device=device
            )
        DetalleBitacora.objects.create(bitacora=bit,accion='CREAR_USUARIO',fecha=timezone.now(),
                                       tabla='Customuser')
        #fin del registtro

        
        headers = self.get_success_headers(ser.data)
        return Response(ser.data, status=status.HTTP_201_CREATED, headers=headers)



class VentaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

class DetalleVentaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer

class PedidoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

class DetallePedidoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer

class FacturaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer

class ReporteViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Reporte.objects.all()
    serializer_class = ReporteSerializer

class BitacoraViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer

class DetalleBitacoraViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = DetalleBitacora.objects.all()
    serializer_class = DetalleBitacoraSerializer



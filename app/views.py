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

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer

class CustomUserViewSet(viewsets.ModelViewSet):
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
    def post(self, request):
        serializer = self.get_serializer(request.user)
        serializer.is_valid(raise_exception=True)
        #--registro en tbitacora
        #quiero registar a la tabla DetalleBitacora


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer

class ReporteViewSet(viewsets.ModelViewSet):
    queryset = Reporte.objects.all()
    serializer_class = ReporteSerializer

class BitacoraViewSet(viewsets.ModelViewSet):
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer

class DetalleBitacoraViewSet(viewsets.ModelViewSet):
    queryset = DetalleBitacora.objects.all()
    serializer_class = DetalleBitacoraSerializer
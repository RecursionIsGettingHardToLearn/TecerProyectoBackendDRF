from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets,status
from  django.utils import timezone

from rest_framework.exceptions import AuthenticationFailed
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
    BitacoraSerializer, DetalleBitacoraSerializer,MyTokenObtainPairSerializer,ChangePasswordSerializer
)
from .models import Bitacora,DetalleBitacora
#permissions
from .permissions import IsAdmin, IsRepartidor, IsCliente
from rest_framework.permissions import AllowAny, IsAuthenticated
# === Auditoría de acciones en Bitácora ===
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
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
    permission_classes = [IsAuthenticated]
    serializer_class = ProductoSerializer

class InventarioViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = InventarioSerializer

class RolViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated]
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
        
        headers = self.get_success_headers(ser.data)
        return Response(ser.data, status=status.HTTP_201_CREATED, headers=headers)
    @action(
        detail=True,
        methods=['post'],
        url_path='set-password',
        permission_classes=[IsAuthenticated,IsAdmin]  # cualquiera autenticado; la lógica de permisos la hace el serializer
    )
    def set_password(self, request, pk=None):
        print("📥 Payload recibido en backend:", request.data)
        """
        Cambia la contraseña del usuario objetivo.
        Reglas:
          - Si cambias TU propia contraseña: debes enviar current_password correcto.
          - Si cambias la de OTRO: debes ser superuser (is_superuser).
          - new_password != current_password y min 6 caracteres (lo valida el serializer).
        Payload esperado:
        {
          "current_password": "opcional si admin, obligatorio si self",
          "new_password": "*****",
          "confirm_new_password": "*****"
        }
        """
        target_user = self.get_object()
        
        ser = ChangePasswordSerializer(
            data=request.data,
            context={"request": request, "user": target_user}
        )
        ser.is_valid(raise_exception=True)

        # Si pasa validación, se setea la nueva contraseña
        new_pwd = ser.validated_data["new_password"]
        target_user.set_password(new_pwd)
        target_user.save(update_fields=["password"])

        # (Opcional) registrar en bitácora esta acción específica
        try:
            self._log(request, "CAMBIAR_PASSWORD", self._tabla())
        except Exception:
            pass

        # 204 sin contenido (front solo necesita saber que fue OK)
        return Response(status=status.HTTP_204_NO_CONTENT)
    @action(
        detail=False,
        methods=['get'],
        url_path='get-superadmins',
        permission_classes=
        [IsAuthenticated]
    )
    def get_superadmind(self ,request):
        qs=CustomUser.objects.filter(is_superuser=True)
        # Imprimir en logs la respuesta
        ser = self.get_serializer(qs, many=True)#El many=True indica que hay varios objetos, no uno solo.
        logger.info("Respuesta get_superadmind: %s", ser.data)
        
        try:
            self._log(request, "LISTAR_SUPERADMINS", self._tabla())
        except Exception:
            pass
        return Response(ser.data, status=status.HTTP_200_OK)

class VentaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = VentaSerializer

class DetalleVentaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DetalleVentaSerializer

class PedidoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PedidoSerializer

class DetallePedidoViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DetallePedidoSerializer

class FacturaViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = FacturaSerializer

class ReporteViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Reporte.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ReporteSerializer

class BitacoraViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = Bitacora.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = BitacoraSerializer

class DetalleBitacoraViewSet(BitacoraLoggerMixin,viewsets.ModelViewSet):
    queryset = DetalleBitacora.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DetalleBitacoraSerializer


class MyTokenObtainPairView(TokenObtainPairView): 
    serializer_class = MyTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user  # ← ESTE es el usuario autenticado

        # IP (X-Forwarded-For si hay proxy; si no, REMOTE_ADDR)
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None

        # User-Agent como "device" (o None si vacío)
        device = request.META.get('HTTP_USER_AGENT') or None

        # Registrar login en bitácora
        Bitacora.objects.create(
            usuario=user,
            login=timezone.now(),
            ip=ip,
            device=device
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf.urls import handler404
from .views import (
    ProductoViewSet, InventarioViewSet, RolViewSet,
    CustomUserViewSet, VentaViewSet, DetalleVentaViewSet,
    PedidoViewSet, DetallePedidoViewSet,
    FacturaViewSet, ReporteViewSet,
    BitacoraViewSet, DetalleBitacoraViewSet,MyTokenObtainPairView
)
from app.autenticacion.auth import LogoutView
router = DefaultRouter()
router.register(r"productos", ProductoViewSet)
router.register(r"inventarios", InventarioViewSet)
router.register(r"roles", RolViewSet)
router.register(r"usuarios", CustomUserViewSet)
router.register(r"ventas", VentaViewSet)
router.register(r"detalle-ventas", DetalleVentaViewSet)
router.register(r"pedidos", PedidoViewSet)
router.register(r"detalle-pedidos", DetallePedidoViewSet)
router.register(r"facturas", FacturaViewSet)
router.register(r"reportes", ReporteViewSet)
router.register(r"bitacoras", BitacoraViewSet)
router.register(r"detalle-bitacoras", DetalleBitacoraViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]
                                
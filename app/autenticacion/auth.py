# app/views/auth.py
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, force_bytes
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from ..models import Bitacora
from ..serializers import MyTokenObtainPairSerializer
from django.utils import timezone
User = get_user_model()
def _get_client_ip(request):
    # Si estás detrás de un proxy, usa X-Forwarded-For
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        RefreshToken(self.token).blacklist()
#vistas

"""
{
  "refresh": "...",
  "password": "..."
}

"""
class LogoutView(APIView):

    permission_classes = [IsAuthenticated]
    def post(self, request):
    
        # invalidamos el refresh token
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # ——————— Registro de logout ———————
        bit = Bitacora.objects.filter(
            usuario=request.user,
            logout__isnull=True
        ).last()
        if bit:
            print('no se esta cerrando seccion ')
            bit.logout = timezone.now()
            bit.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
    

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
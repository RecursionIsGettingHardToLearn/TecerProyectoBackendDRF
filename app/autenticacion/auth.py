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
from django.utils import timezone
User = get_user_model()
def _get_client_ip(request):
    # Si estás detrás de un proxy, usa X-Forwarded-For
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
#Serializadores
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user with this email')
        return value

class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, write_only=True)
    token = serializers.CharField(write_only=True)
    uid = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except Exception:
            raise serializers.ValidationError('Invalid UID')
        token = attrs['token']
        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError('Invalid or expired token')
        user.set_password(attrs['password'])
        user.save()
        return attrs

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
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc1NDU3ODEwNCwiaWF0IjoxNzU0NDkxNzA0LCJqdGkiOiI3Y2E2NTcyNzcxODk0NTJjYmIwYWU1MjIyYWVlMmJjZiIsInVzZXJfaWQiOiIxIn0.oc6d4l1RoPzdfJSQhTfij1In4afW5qiDz2xKb-glTW0",
  "password": "angelica2025"
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
    
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=serializer.validated_data['email'])
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/password-reset-confirm/{uidb64}/{token}/"
        # Aquí tu lógica de envío de correo electrónico con reset_url
        return Response({'message': 'Reset link sent'}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SetNewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'message': 'Password has been reset.'}, status=status.HTTP_200_OK)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)  # valida credenciales
        except Exception as e:
            # Unifica mensaje de error a tu gusto
            raise serializers.ValidationError('Credenciales inválidas.') from e

        # (Opcional) agrega info del usuario al payload que devolverás al FE
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'rol': getattr(getattr(self.user, 'rol', None), 'nombre', None),
        }
        return data

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer   # ← usa el tuyo

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
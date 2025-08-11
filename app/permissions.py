# permissions.py
from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

class IsRepartidor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Repartidor'

class IsCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Cliente'

class IsCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Cajero'        
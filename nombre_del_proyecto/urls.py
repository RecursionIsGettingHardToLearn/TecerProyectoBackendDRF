# project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf.urls import handler404
from rest_framework.exceptions import NotFound  # ← excepción DRF

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("app.urls")),
]

def api_handler_404(request, exception=None):
    if request.path.startswith("/api/"):
        exc = NotFound()  # detail="Not found.", default_code="not_found"
        return JsonResponse(
            {
                "error": {
                    "message": "Endpoint no encontrado",
                    "code": exc.default_code.upper(),  # usa mismo formato que exceptions.py
                    "fields": {}
                }
            },
            status=404
        )

    from django.views.defaults import page_not_found
    return page_not_found(request, exception, template_name="404.html")

handler404 = "nombre_del_proyecto.urls.api_handler_404"

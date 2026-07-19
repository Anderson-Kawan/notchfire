from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def healthcheck(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse(
            {"status": "unhealthy", "database": "unavailable"},
            status=503,
        )

    return JsonResponse({"status": "ok", "database": "ok"})

urlpatterns = [
    path('healthz/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('api/', include('core.urls_api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import logging

from django.http import JsonResponse

from .tenancy import activate_empresa, deactivate_empresa


logger = logging.getLogger(__name__)


class ApiExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        is_api_request = (
            request.path.startswith('/api/')
            or request.headers.get('x-requested-with') == 'XMLHttpRequest'
        )
        if not is_api_request:
            return None

        logger.exception(
            'Erro não tratado em requisição API %s %s',
            request.method,
            request.path,
            exc_info=True,
        )
        return JsonResponse({
            'success': False,
            'error': 'Não foi possível concluir a ação. Tente novamente ou chame o suporte.',
        }, status=500)


class EmpresaAtivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = activate_empresa(request)
        try:
            return self.get_response(request)
        finally:
            deactivate_empresa(token)

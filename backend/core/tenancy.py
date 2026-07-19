from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http.request import split_domain_port

from .tenant_context import reset_current_empresa, set_current_empresa


def _normalizar_host(host):
    host, _ = split_domain_port(host or "")
    return host.rstrip(".").lower()


def _host_da_requisicao(request):
    try:
        return _normalizar_host(request.get_host())
    except Exception:
        return ""


def _subdominio_para_slug(host):
    for base_domain in getattr(settings, "TENANT_BASE_DOMAINS", []):
        base_domain = _normalizar_host(base_domain)
        if not base_domain or host == base_domain:
            continue

        suffix = f".{base_domain}"
        if not host.endswith(suffix):
            continue

        subdominio = host[: -len(suffix)]
        if "." in subdominio:
            return None

        if subdominio in getattr(settings, "TENANT_RESERVED_SUBDOMAINS", []):
            return None

        return subdominio

    return None


def resolve_empresa_por_host(request):
    host = _host_da_requisicao(request)
    if not host:
        return None

    from .models import Empresa

    empresa = Empresa.objects.filter(dominio__iexact=host, ativa=True).first()
    if empresa:
        return empresa

    slug = _subdominio_para_slug(host)
    if not slug:
        return None

    return Empresa.objects.filter(slug__iexact=slug, ativa=True).first()


def resolve_empresa_ativa(request, user=None):
    user = user or getattr(request, "user", None)
    request.empresa_por_host = resolve_empresa_por_host(request)
    request.empresa_acesso_negado = False

    if not user or not user.is_authenticated:
        return None

    from .models import EmpresaUsuario

    vinculos = (
        EmpresaUsuario.objects
        .select_related("empresa")
        .filter(user=user, ativo=True, empresa__ativa=True)
    )

    session = getattr(request, "session", None)

    if request.empresa_por_host:
        vinculo = vinculos.filter(empresa=request.empresa_por_host).first()
        if vinculo:
            if session is not None:
                session["empresa_ativa_id"] = vinculo.empresa_id
            return vinculo.empresa

        if session is not None:
            session.pop("empresa_ativa_id", None)
        request.empresa_acesso_negado = True
        return None

    empresa_id = session.get("empresa_ativa_id") if session is not None else None
    if empresa_id:
        vinculo = vinculos.filter(empresa_id=empresa_id).first()
        if vinculo:
            return vinculo.empresa
        if session is not None:
            session.pop("empresa_ativa_id", None)

    vinculo = vinculos.order_by("empresa__nome", "id").first()
    if vinculo:
        if session is not None:
            session["empresa_ativa_id"] = vinculo.empresa_id
        return vinculo.empresa

    return None


def activate_empresa(request, user=None):
    empresa = resolve_empresa_ativa(request, user=user)
    request.empresa_ativa = empresa
    if getattr(request, "empresa_acesso_negado", False):
        raise PermissionDenied("Usuário sem acesso a esta empresa.")
    return set_current_empresa(empresa)


def deactivate_empresa(token):
    reset_current_empresa(token)

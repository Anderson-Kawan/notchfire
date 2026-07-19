from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Prefetch
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import timedelta, date
import calendar
import csv
import json
import logging
from django.utils import timezone
from django.utils.dateparse import parse_date
from .models import (
    EmpresaUsuario, Equipamento, Grupo, Departamento, UsuarioPerfil,
    TipoServico, Periodicidade, TipoEquipamento, Predio,
    Inspecao, ItemChecklist, SecaoChecklist, Servico,
    RespostaChecklist, AcaoCorretiva, ServicoTipoEquipamento,
    RelatorioGerado
)

from .forms import (
    EquipamentoForm, GrupoForm, DepartamentoForm,
    UsuarioForm, TipoServicoForm, PeriodicidadeForm,
    InspecaoForm, PredioForm, TipoEquipamentoForm,
    ServicoTipoEquipamentoForm, SecaoChecklistForm, ItemChecklistForm,
)
from .notifications import notificar_checklist_nao_atende


logger = logging.getLogger(__name__)

ERRO_GENERICO_API = 'Não foi possível concluir a ação. Tente novamente ou chame o suporte.'


def _json_exception(exc, message=ERRO_GENERICO_API, status=500, context='Erro inesperado na API'):
    logger.exception('%s: %s', context, exc)
    return JsonResponse({'success': False, 'error': message}, status=status)


def _json_integrity_exception(exc, message='Já existe um registro com estes dados. Verifique as informações e tente novamente.'):
    return _json_exception(exc, message=message, status=400, context='Erro de integridade no banco de dados')


def _json_checklist_duplicado(exc):
    return _json_integrity_exception(
        exc,
        message='Já existe um checklist com esta periodicidade para este tipo de equipamento.'
    )


def _add_months(data, meses):
    mes = data.month - 1 + meses
    ano = data.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return data.replace(year=ano, month=mes, day=dia)


def _calcular_proximo_vencimento(data_base, periodicidade):
    if not data_base or not periodicidade or periodicidade.por_demanda or not periodicidade.valor:
        return None

    valor = periodicidade.valor

    if periodicidade.tipo == 'dias':
        return data_base + timedelta(days=valor)
    if periodicidade.tipo == 'semanas':
        return data_base + timedelta(weeks=valor)
    if periodicidade.tipo == 'meses':
        return _add_months(data_base, valor)
    if periodicidade.tipo == 'anos':
        return _add_months(data_base, valor * 12)

    return None


def _data_iso(data):
    return data.isoformat() if data else ''


def _data_br(data):
    return data.strftime('%d/%m/%Y') if data else ''


def _equipamento_vencimentos_data(equipamento):
    return {
        'possui_vencimento': equipamento.possui_vencimento,
        'data_vencimento': _data_iso(equipamento.data_vencimento),
        'data_vencimento_formatada': _data_br(equipamento.data_vencimento),
        'vencimento_carga': _data_iso(equipamento.vencimento_carga),
        'vencimento_carga_formatado': _data_br(equipamento.vencimento_carga),
        'vencimento_teste_hidrostatico': _data_iso(equipamento.vencimento_teste_hidrostatico),
        'vencimento_teste_hidrostatico_formatado': _data_br(equipamento.vencimento_teste_hidrostatico),
        'is_extintor': equipamento.is_extintor(),
    }


def _arquivo_absoluto_url(request, field):
    if not field:
        return ''

    try:
        return request.build_absolute_uri(field.url)
    except ValueError:
        return ''


def _equipamento_codigo(equipamento):
    return equipamento.numero_serie or equipamento.numero_extintor or equipamento.numero_cilindro or ''


def _equipamento_localizacao_texto(equipamento):
    partes = []
    if equipamento.predio:
        partes.append(equipamento.predio.nome)
    if equipamento.departamento:
        partes.append(equipamento.departamento.nome)
    if equipamento.local:
        partes.append(equipamento.local)
    return ' · '.join(partes)


def _equipamento_navegacao_data(request, equipamento):
    tipo = equipamento.tipo_equipamento
    grupo = equipamento.grupo
    predio = equipamento.predio
    departamento = equipamento.departamento

    return {
        'id': equipamento.id,
        'nome': equipamento.nome,
        'codigo': _equipamento_codigo(equipamento),
        'numero_serie': equipamento.numero_serie or equipamento.numero_extintor or '',
        'numero_cilindro': equipamento.numero_cilindro or '',
        'marca': equipamento.marca or '',
        'tipo_equipamento_id': tipo.id if tipo else None,
        'tipo_equipamento_nome': tipo.nome if tipo else '',
        'tipo_nome': tipo.nome if tipo else '',
        'grupo_id': grupo.id if grupo else None,
        'grupo_nome': grupo.nome if grupo else '',
        'predio_id': predio.id if predio else None,
        'predio_nome': predio.nome if predio else '',
        'departamento_id': departamento.id if departamento else None,
        'departamento_nome': departamento.nome if departamento else '',
        'local': equipamento.local or '',
        'localizacao': _equipamento_localizacao_texto(equipamento),
        'ponto_referencia': equipamento.ponto_referencia or '',
        'descricao': equipamento.descricao or '',
        'observacoes': equipamento.observacoes or '',
        'foto_url': _arquivo_absoluto_url(request, equipamento.foto),
        'qr_code_url': _arquivo_absoluto_url(request, equipamento.qr_code),
        'status': equipamento.ativo,
        'ativo': equipamento.ativo,
        'detalhe_url': f'/equipamentos/{equipamento.id}/',
        'criado_em': equipamento.criado_em.strftime('%Y-%m-%d %H:%M'),
        **_equipamento_vencimentos_data(equipamento),
    }


def _filtrar_equipamentos_por_busca(queryset, busca):
    if not busca:
        return queryset

    return queryset.filter(
        Q(nome__icontains=busca) |
        Q(numero_serie__icontains=busca) |
        Q(numero_extintor__icontains=busca) |
        Q(numero_cilindro__icontains=busca) |
        Q(marca__icontains=busca) |
        Q(local__icontains=busca) |
        Q(ponto_referencia__icontains=busca) |
        Q(descricao__icontains=busca) |
        Q(observacoes__icontains=busca) |
        Q(predio__nome__icontains=busca) |
        Q(departamento__nome__icontains=busca) |
        Q(tipo_equipamento__nome__icontains=busca) |
        Q(grupo__nome__icontains=busca)
    )


def _aplicar_filtro_status(queryset, status_param, ativo_padrao=None):
    status_normalizado = (status_param or '').strip().lower()
    if status_normalizado in ['ativo', 'ativos', 'true', '1']:
        return queryset.filter(ativo=True)
    if status_normalizado in ['inativo', 'inativos', 'false', '0']:
        return queryset.filter(ativo=False)
    if status_normalizado in ['todos', 'todas', 'all']:
        return queryset
    if ativo_padrao is not None:
        return queryset.filter(ativo=ativo_padrao)
    return queryset


def _predio_navegacao_data(predio):
    return {
        'id': predio.id,
        'nome': predio.nome,
        'descricao': predio.descricao or '',
        'endereco': predio.endereco or '',
        'ativo': predio.ativo,
        'status': predio.ativo,
        'departamentos_count': getattr(predio, 'departamentos_count', 0),
        'equipamentos_count': getattr(predio, 'equipamentos_count', 0),
    }


def _departamento_navegacao_data(departamento):
    predio = departamento.predio
    return {
        'id': departamento.id,
        'nome': departamento.nome,
        'descricao': departamento.descricao or '',
        'localizacao': departamento.localizacao or '',
        'responsavel': departamento.responsavel or '',
        'email': departamento.email or '',
        'telefone': departamento.telefone or '',
        'predio_id': predio.id if predio else None,
        'predio_nome': predio.nome if predio else '',
        'ativo': departamento.ativo,
        'status': departamento.ativo,
        'equipamentos_count': getattr(departamento, 'equipamentos_count', 0),
    }


def _departamento_predio_api_data(departamento):
    predio = departamento.predio
    return {
        'id': departamento.id,
        'nome': departamento.nome,
        'predio_id': predio.id if predio else None,
        'predio_nome': predio.nome if predio else '',
    }


def _equipamento_departamento_api_data(equipamento):
    departamento = equipamento.departamento
    predio = equipamento.predio or (departamento.predio if departamento else None)
    return {
        'id': equipamento.id,
        'nome': equipamento.nome,
        'codigo': _equipamento_codigo(equipamento),
        'departamento_id': departamento.id if departamento else None,
        'departamento_nome': departamento.nome if departamento else '',
        'predio_id': predio.id if predio else None,
        'predio_nome': predio.nome if predio else '',
        'status': 'ativo' if equipamento.ativo else 'inativo',
        'ativo': equipamento.ativo,
        'detalhe_url': f'/equipamentos/{equipamento.id}/',
    }


def _tipo_equipamento_is_extintor(tipo):
    if not tipo:
        return False

    grupo_nome = tipo.grupo.nome if getattr(tipo, 'grupo', None) else ''
    return 'extintor' in f'{tipo.nome} {grupo_nome}'.lower()


def _serialize_editor_servico(servico):
    secoes = []
    for secao in servico.secoes_checklist.filter(ativo=True).order_by('ordem', 'nome'):
        itens = []
        for item in secao.itens.filter(ativo=True).order_by('ordem', 'id'):
            itens.append({
                'id': item.id,
                'pergunta': item.pergunta,
                'tipo_resposta': item.tipo_resposta,
                'detalhamento': item.detalhamento or '',
                'ordem': item.ordem,
                'obrigatorio': item.obrigatorio,
                'imagem': item.imagem_descritiva.url if item.imagem_descritiva else '',
            })

        secoes.append({
            'id': secao.id,
            'nome': secao.nome,
            'descricao': secao.descricao or '',
            'ordem': secao.ordem,
            'itens': itens,
        })

    total_itens = sum(len(secao['itens']) for secao in secoes)

    return {
        'id': servico.id,
        'tipo_servico_id': servico.tipo_servico_id,
        'tipo_servico_nome': servico.tipo_servico.nome if servico.tipo_servico else 'Sem checklist',
        'periodicidade_id': servico.periodicidade_id,
        'periodicidade_nome': servico.periodicidade.get_rotulo_inspecao() if servico.periodicidade else 'Sem periodicidade',
        'obrigatorio': servico.obrigatorio,
        'vencimento_final_mes': servico.vencimento_final_mes,
        'habilitar_assinatura': servico.habilitar_assinatura,
        'assinatura_obrigatoria': servico.assinatura_obrigatoria,
        'acoes_obrigatorias': servico.acoes_obrigatorias,
        'permitir_servicos_massa': servico.permitir_servicos_massa,
        'ativo': servico.ativo,
        'ordem': servico.ordem,
        'secoes_count': len(secoes),
        'itens_count': total_itens,
        'secoes': secoes,
    }


def _editor_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _editor_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sync_editor_checklist(servico, secoes_payload):
    if secoes_payload is None:
        return

    if not isinstance(secoes_payload, list):
        raise ValidationError('As seções do checklist devem ser enviadas em formato de lista.')

    secao_ids_mantidas = []
    item_ids_mantidos = []

    for secao_index, secao_data in enumerate(secoes_payload):
        if not isinstance(secao_data, dict):
            raise ValidationError('Dados da seção inválidos.')

        nome_secao = (secao_data.get('nome') or '').strip()
        if not nome_secao:
            raise ValidationError('Nome da seção é obrigatório.')

        secao_id = _editor_positive_int(secao_data.get('id'))
        if secao_id:
            secao = servico.secoes_checklist.filter(id=secao_id).first()
            if not secao:
                raise ValidationError('Seção inválida para este checklist.')
        else:
            secao = SecaoChecklist(servico_tipo_equipamento=servico)

        secao.nome = nome_secao
        secao.descricao = secao_data.get('descricao') or ''
        secao.ordem = _editor_int(secao_data.get('ordem'), secao_index)
        secao.ativo = secao_data.get('ativo', True)
        secao.save()
        secao_ids_mantidas.append(secao.id)

        itens_payload = secao_data.get('itens') or []
        if not isinstance(itens_payload, list):
            raise ValidationError('As perguntas da seção devem ser enviadas em formato de lista.')

        for item_index, item_data in enumerate(itens_payload):
            if not isinstance(item_data, dict):
                raise ValidationError('Dados da pergunta inválidos.')

            pergunta = (item_data.get('pergunta') or '').strip()
            if not pergunta:
                raise ValidationError('Pergunta é obrigatória.')

            item_id = _editor_positive_int(item_data.get('id'))
            if item_id:
                item = ItemChecklist.objects.filter(
                    id=item_id,
                    secao__servico_tipo_equipamento=servico,
                ).first()
                if not item:
                    raise ValidationError('Pergunta inválida para este checklist.')
                item.secao = secao
            else:
                item = ItemChecklist(secao=secao)

            item.pergunta = pergunta
            item.tipo_resposta = item_data.get('tipo_resposta') or 'sim_nao'
            item.detalhamento = item_data.get('detalhamento') or ''
            item.ordem = _editor_int(item_data.get('ordem'), item_index)
            item.obrigatorio = item_data.get('obrigatorio', True)
            item.ativo = item_data.get('ativo', True)
            item.save()
            item_ids_mantidos.append(item.id)

    ItemChecklist.objects.filter(
        secao__servico_tipo_equipamento=servico,
    ).exclude(id__in=item_ids_mantidos).delete()
    servico.secoes_checklist.exclude(id__in=secao_ids_mantidas).delete()



def index(request):
    return redirect('login')


def login_view(request):
    erro = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            erro = 'Usuário ou senha inválidos.'

    return render(request, 'core/login.html', {'erro': erro})


@login_required
def home_view(request):
    return render(request, 'core/home.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


def is_superuser(user):
    return user.is_superuser


@user_passes_test(is_superuser)
def criar_usuario_view(request):
    return redirect('usuarios')


@user_passes_test(is_superuser)
def usuarios_view(request):
    return render(request, 'core/usuarios.html', {
        'tipo_acesso_choices': [
            ('admin', 'Administrador'),
            ('supervisor', 'Supervisor'),
            ('analista', 'Analista'),
            ('usuario', 'Usuário'),
        ],
        'predios': Predio.objects.filter(ativo=True).order_by('nome'),
    })


def _usuario_tipo_acesso(user):
    perfil = getattr(user, 'perfil', None)
    if perfil:
        return perfil.tipo_acesso, perfil.get_tipo_acesso_display()
    if user.is_superuser:
        return 'admin', 'Administrador'
    if user.is_staff:
        return 'analista', 'Analista'
    return 'usuario', 'Usuário'


def _usuario_status(user):
    perfil = getattr(user, 'perfil', None)
    if perfil:
        return perfil.status, perfil.get_status_display()
    return ('ativo' if user.is_active else 'inativo'), ('Ativo' if user.is_active else 'Inativo')


def _usuario_sites(user):
    perfil = getattr(user, 'perfil', None)
    if perfil:
        return perfil.sites, perfil.get_sites_display()
    return '', '-'


def _formatar_data_usuario(data):
    if not data:
        return 'Nunca'
    return timezone.localtime(data).strftime('%d/%m/%Y %H:%M')


def _usuario_vistoriador_observacoes(observacoes):
    texto = observacoes or ''
    marcador = 'Acesso de Vistoriador habilitado.'
    vistoriador = marcador in texto
    observacoes_limpas = texto.replace(marcador, '').strip()
    return vistoriador, observacoes_limpas


def _aplicar_permissoes_usuario(user, tipo_acesso, status):
    user.is_active = status != 'inativo'

    if tipo_acesso == 'admin':
        user.is_staff = True
        user.is_superuser = True
    elif tipo_acesso in ['supervisor', 'analista']:
        user.is_staff = True
        user.is_superuser = False
    else:
        user.is_staff = False
        user.is_superuser = False


def _serializar_usuario(user):
    tipo_valor, tipo_label = _usuario_tipo_acesso(user)
    status_valor, status_label = _usuario_status(user)
    site_valor, site_label = _usuario_sites(user)
    nome = user.get_full_name() or user.username or user.email
    perfil = getattr(user, 'perfil', None)
    ultimo_acesso = perfil.ultimo_acesso if perfil and perfil.ultimo_acesso else user.last_login
    observacoes = perfil.observacoes if perfil else ''
    vistoriador, observacoes_limpas = _usuario_vistoriador_observacoes(observacoes)
    predio = perfil.predio if perfil and perfil.predio else None

    return {
        'id': user.id,
        'nome': nome,
        'email': user.email,
        'username': user.username,
        'iniciais': ''.join([parte[:1] for parte in nome.split()[:2]]).upper() or 'US',
        'tipo_acesso': tipo_valor,
        'tipo_acesso_label': tipo_label,
        'sites': site_valor,
        'sites_label': site_label,
        'predio_id': predio.id if predio else '',
        'predio_nome': predio.nome if predio else '-',
        'foto_url': perfil.foto.url if perfil and perfil.foto else '',
        'status': status_valor,
        'status_label': status_label,
        'filtros': perfil.filtros if perfil and perfil.filtros else '',
        'observacoes': observacoes_limpas,
        'vistoriador': vistoriador,
        'ultimo_acesso': _formatar_data_usuario(ultimo_acesso),
        'criado_em': _formatar_data_usuario(user.date_joined),
}


def _sincronizar_empresa_usuario(request, user, tipo_acesso):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        return

    EmpresaUsuario.objects.update_or_create(
        empresa=empresa,
        user=user,
        defaults={
            'tipo_acesso': tipo_acesso,
            'ativo': True,
        },
    )


def _request_usuario_data(request):
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        return request.POST
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _validar_payload_usuario(data, user=None):
    nome_completo = data.get('nome', '').strip()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    tipo_acesso = data.get('tipo_acesso', 'analista')
    predio_id = data.get('predio_id', '')
    status = data.get('status', 'ativo')

    tipos_validos = ['admin', 'supervisor', 'analista', 'usuario']
    status_validos = [choice[0] for choice in UsuarioPerfil.STATUS_CHOICES]

    if not nome_completo:
        return None, 'Informe o nome completo.'
    if not username:
        return None, 'Informe o nome de login.'
    if not email:
        return None, 'Informe o e-mail.'
    if not user and not password:
        return None, 'Informe a senha.'
    if password and len(password) < 8:
        return None, 'A senha precisa ter pelo menos 8 caracteres.'

    try:
        validate_email(email)
    except ValidationError:
        return None, 'Informe um e-mail válido.'

    usuarios_email = User.objects.filter(email__iexact=email)
    if user:
        usuarios_email = usuarios_email.exclude(id=user.id)
    if usuarios_email.exists():
        return None, 'Este e-mail já está cadastrado.'

    usuarios_login = User.objects.filter(username__iexact=username)
    if user:
        usuarios_login = usuarios_login.exclude(id=user.id)
    if usuarios_login.exists():
        return None, 'Este nome de login já está em uso.'

    if tipo_acesso not in tipos_validos:
        return None, 'Tipo de acesso inválido.'
    if status not in status_validos:
        return None, 'Status inválido.'

    predio = None
    if predio_id:
        try:
            predio = Predio.objects.get(id=predio_id, ativo=True)
        except Predio.DoesNotExist:
            return None, 'Prédio inválido.'
    else:
        return None, 'Selecione um prédio.'

    return {
        'nome_completo': nome_completo,
        'username': username,
        'email': email,
        'password': password,
        'tipo_acesso': tipo_acesso,
        'predio': predio,
        'status': status,
        'filtros': data.get('filtros', '').strip(),
        'observacoes': data.get('observacoes', '').strip(),
        'vistoriador': bool(data.get('vistoriador', False)),
    }, None


@login_required
@user_passes_test(is_superuser)
@require_http_methods(["GET"])
def api_usuarios_listar(request):
    try:
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '').strip()
        tipo_acesso = request.GET.get('tipo_acesso', '').strip()
        predio_id = request.GET.get('predio_id', '').strip()

        usuarios_base = User.objects.select_related('perfil').all()
        empresa = getattr(request, 'empresa_ativa', None)
        if empresa:
            usuarios_base = usuarios_base.filter(
                empresas__empresa=empresa,
                empresas__ativo=True,
            ).distinct()
        usuarios = usuarios_base

        if search:
            usuarios = usuarios.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(perfil__predio__nome__icontains=search) |
                Q(perfil__filtros__icontains=search) |
                Q(perfil__observacoes__icontains=search)
            )

        if status == 'ativo':
            usuarios = usuarios.filter(Q(perfil__status='ativo') | Q(perfil__isnull=True, is_active=True))
        elif status == 'inativo':
            usuarios = usuarios.filter(Q(perfil__status='inativo') | Q(perfil__isnull=True, is_active=False))
        elif status == 'pendente':
            usuarios = usuarios.filter(perfil__status='pendente')

        if tipo_acesso == 'admin':
            usuarios = usuarios.filter(Q(perfil__tipo_acesso='admin') | Q(perfil__isnull=True, is_superuser=True))
        elif tipo_acesso == 'supervisor':
            usuarios = usuarios.filter(perfil__tipo_acesso='supervisor')
        elif tipo_acesso == 'analista':
            usuarios = usuarios.filter(Q(perfil__tipo_acesso='analista') | Q(perfil__isnull=True, is_staff=True, is_superuser=False))
        elif tipo_acesso:
            usuarios = usuarios.filter(perfil__tipo_acesso=tipo_acesso)

        if predio_id:
            usuarios = usuarios.filter(perfil__predio_id=predio_id)

        usuarios = usuarios.order_by('first_name', 'last_name', 'email') if sort == 'asc' else usuarios.order_by('-first_name', '-last_name', '-email')

        total = usuarios.count()
        total_ativos = usuarios_base.filter(Q(perfil__status='ativo') | Q(perfil__isnull=True, is_active=True)).count()
        total_convites = usuarios_base.filter(perfil__status='pendente').count()
        total_admins = usuarios_base.filter(Q(perfil__tipo_acesso='admin') | Q(perfil__isnull=True, is_superuser=True)).count()

        start = (page - 1) * rows
        usuarios_paginados = usuarios[start:start + rows]

        dados = [_serializar_usuario(user) for user in usuarios_paginados]

        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_convites': total_convites,
            'total_admins': total_admins,
            'page': page,
            'rows': rows,
        })
    except IntegrityError as e:
        return _json_integrity_exception(e)
    except Exception as e:
        return _json_exception(e)


@login_required
@user_passes_test(is_superuser)
@require_http_methods(["POST"])
@csrf_exempt
def api_usuarios_criar(request):
    try:
        data = _request_usuario_data(request)
        payload, error = _validar_payload_usuario(data)

        if error:
            return JsonResponse({'success': False, 'error': error}, status=400)

        partes_nome = payload['nome_completo'].split()
        user = User.objects.create_user(
            username=payload['username'],
            email=payload['email'],
            password=payload['password'],
            first_name=partes_nome[0],
            last_name=' '.join(partes_nome[1:]),
            is_active=payload['status'] != 'inativo',
        )

        _aplicar_permissoes_usuario(user, payload['tipo_acesso'], payload['status'])
        user.save()

        observacoes = payload['observacoes']
        if payload['vistoriador']:
            observacoes = f'{observacoes}\nAcesso de Vistoriador habilitado.'.strip()

        perfil = UsuarioPerfil.objects.create(
            user=user,
            tipo_acesso=payload['tipo_acesso'],
            predio=payload['predio'],
            filtros=payload['filtros'],
            status=payload['status'],
            observacoes=observacoes,
        )

        if request.FILES.get('foto'):
            perfil.foto = request.FILES['foto']
            perfil.save()

        _sincronizar_empresa_usuario(request, user, payload['tipo_acesso'])

        return JsonResponse({
            'success': True,
            'message': f'Usuário "{perfil.get_nome_completo()}" criado com sucesso!',
            'data': {'id': user.id}
        })
    except IntegrityError as e:
        return _json_integrity_exception(e)
    except Exception as e:
        return _json_exception(e)


@login_required
@user_passes_test(is_superuser)
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
@csrf_exempt
def api_usuarios_detalhe(request, id):
    try:
        user = get_object_or_404(User.objects.select_related('perfil'), id=id)

        if request.method == 'GET':
            return JsonResponse({'success': True, 'data': _serializar_usuario(user)})

        if request.method == 'DELETE':
            if user.id == request.user.id:
                return JsonResponse({'success': False, 'error': 'Você não pode excluir o próprio usuário logado.'}, status=400)

            nome = user.get_full_name() or user.username
            user.delete()
            return JsonResponse({'success': True, 'message': f'Usuário "{nome}" excluído com sucesso!'})

        data = _request_usuario_data(request)
        payload, error = _validar_payload_usuario(data, user=user)

        if error:
            return JsonResponse({'success': False, 'error': error}, status=400)

        partes_nome = payload['nome_completo'].split()
        user.first_name = partes_nome[0]
        user.last_name = ' '.join(partes_nome[1:])
        user.username = payload['username']
        user.email = payload['email']
        if payload['password']:
            user.set_password(payload['password'])
        _aplicar_permissoes_usuario(user, payload['tipo_acesso'], payload['status'])
        user.save()

        observacoes = payload['observacoes']
        if payload['vistoriador']:
            observacoes = f'{observacoes}\nAcesso de Vistoriador habilitado.'.strip()

        perfil, _ = UsuarioPerfil.objects.get_or_create(user=user)
        perfil.tipo_acesso = payload['tipo_acesso']
        perfil.predio = payload['predio']
        perfil.filtros = payload['filtros']
        perfil.status = payload['status']
        perfil.observacoes = observacoes
        if request.FILES.get('foto'):
            perfil.foto = request.FILES['foto']
        perfil.save()
        _sincronizar_empresa_usuario(request, user, payload['tipo_acesso'])

        return JsonResponse({
            'success': True,
            'message': f'Usuário "{perfil.get_nome_completo()}" atualizado com sucesso!',
            'data': _serializar_usuario(User.objects.select_related('perfil').get(id=user.id)),
        })
    except Exception as e:
        return _json_exception(e)


# VIEWS PARA GRUPOS
@login_required
def grupos_view(request):
    """View para listar grupos"""
    return render(request, 'core/grupos.html')

@login_required
@require_http_methods(["GET"])
def api_equipamentos_listar(request):
    """API para listar equipamentos com filtros e paginação"""
    try:
        search = (request.GET.get('search') or request.GET.get('q') or '').strip()
        page = int(request.GET.get('page', 1))
        rows = int(request.GET.get('rows', 10))
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '')
        predio_id = request.GET.get('predio_id', '').strip()
        departamento_id = request.GET.get('departamento_id', '').strip()
        grupo_id = request.GET.get('grupo_id', '').strip()
        tipo_equipamento_id = request.GET.get('tipo_equipamento_id', '').strip()
        
        equipamentos = Equipamento.objects.select_related(
            'tipo_equipamento',
            'grupo',
            'predio',
            'departamento',
        ).all()
        
        equipamentos = _filtrar_equipamentos_por_busca(equipamentos, search)

        if predio_id:
            equipamentos = equipamentos.filter(predio_id=predio_id)
        if departamento_id:
            equipamentos = equipamentos.filter(departamento_id=departamento_id)
        if grupo_id:
            equipamentos = equipamentos.filter(grupo_id=grupo_id)
        if tipo_equipamento_id:
            equipamentos = equipamentos.filter(tipo_equipamento_id=tipo_equipamento_id)

        equipamentos = _aplicar_filtro_status(equipamentos, status)
        
        if sort == 'asc':
            equipamentos = equipamentos.order_by('nome')
        else:
            equipamentos = equipamentos.order_by('-nome')
        
        total = equipamentos.count()
        total_ativos = equipamentos.filter(ativo=True).count()
        total_inativos = equipamentos.filter(ativo=False).count()
        total_tipos = equipamentos.values('tipo_equipamento_id').exclude(tipo_equipamento_id=None).distinct().count()
        start = (page - 1) * rows
        end = start + rows
        equipamentos_paginados = equipamentos[start:end]
        
        dados = []
        for equip in equipamentos_paginados:
            dados.append(_equipamento_navegacao_data(request, equip))
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_inativos': total_inativos,
            'total_tipos': total_tipos,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["GET"])
def api_grupos_listar(request):
    """API para listar grupos com filtros e paginação"""
    try:
        grupo_id = request.GET.get('id')
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '').strip()
        
        grupos_base = Grupo.objects.prefetch_related('equipamentos').all()
        grupos = grupos_base

        if grupo_id:
            grupos = grupos.filter(id=grupo_id)
        
        if search:
            grupos = grupos.filter(
                Q(nome__icontains=search) |
                Q(descricao__icontains=search)
            )

        if status == 'ativo':
            grupos = grupos.filter(ativo=True)
        elif status == 'inativo':
            grupos = grupos.filter(ativo=False)
        
        if sort == 'asc':
            grupos = grupos.order_by('nome')
        else:
            grupos = grupos.order_by('-nome')
        
        total = grupos.count()
        total_ativos = grupos_base.filter(ativo=True).count()
        total_inativos = grupos_base.filter(ativo=False).count()
        total_equipamentos = Equipamento.objects.filter(grupo__isnull=False).count()
        
        start = (page - 1) * rows
        grupos_paginados = grupos[start:start + rows]
        
        dados = []
        for grupo in grupos_paginados:
            dados.append({
                'id': grupo.id,
                'nome': grupo.nome,
                'descricao': grupo.descricao or '',
                'equipamentos': grupo.equipamentos.count(),
                'status': grupo.ativo,
                'criado_em': grupo.criado_em.strftime('%Y-%m-%d'),
            })
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_inativos': total_inativos,
            'total_equipamentos': total_equipamentos,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_grupos_criar(request):
    """API para criar um novo grupo"""
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do grupo é obrigatório'
            }, status=400)
        
        # Verificar se grupo já existe
        if Grupo.objects.filter(nome=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um grupo com o nome "{nome}"'
            }, status=400)
        
        # Criar grupo
        grupo = Grupo.objects.create(
            nome=nome,
            descricao=descricao,
            ativo=status
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{nome}" criado com sucesso!',
            'data': {
                'id': grupo.id,
                'nome': grupo.nome,
                'descricao': grupo.descricao,
                'status': grupo.ativo,
                'criado_em': grupo.criado_em.strftime('%Y-%m-%d'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_grupos_editar(request, id):
    """API para editar um grupo"""
    try:
        grupo = get_object_or_404(Grupo, id=id)
        data = json.loads(request.body)
        
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do grupo é obrigatório'
            }, status=400)
        
        # Verificar se nome já existe (exceto o próprio grupo)
        if Grupo.objects.filter(nome=nome).exclude(id=id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um grupo com o nome "{nome}"'
            }, status=400)
        
        # Atualizar grupo
        grupo.nome = nome
        grupo.descricao = descricao
        grupo.ativo = status
        grupo.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{nome}" atualizado com sucesso!',
            'data': {
                'id': grupo.id,
                'nome': grupo.nome,
                'descricao': grupo.descricao,
                'status': grupo.ativo,
                'criado_em': grupo.criado_em.strftime('%Y-%m-%d'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_grupos_excluir(request, id):
    """API para excluir um grupo"""
    try:
        grupo = get_object_or_404(Grupo, id=id)
        
        # Verificar se tem equipamentos
        quantidade_equipamentos = grupo.equipamentos.count()
        if quantidade_equipamentos > 0:
            return JsonResponse({
                'success': False,
                'error': f'Não é possível excluir o grupo "{grupo.nome}" pois ele possui {quantidade_equipamentos} equipamento(s) vinculado(s).'
            }, status=400)
        
        nome = grupo.nome
        grupo.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{nome}" excluído com sucesso!'
        })
    except Exception as e:
        return _json_exception(e)


@login_required
def equipamentos_view(request):
    busca = request.GET.get('q', '').strip()
    equipamentos = Equipamento.objects.all().order_by('-id')

    if busca:
        equipamentos = equipamentos.filter(
            Q(nome__icontains=busca) |
            Q(numero_extintor__icontains=busca) |
            Q(numero_cilindro__icontains=busca) |
            Q(local__icontains=busca)
        )

    return render(request, 'core/equipamentos.html', {
        'equipamentos': equipamentos,
        'busca': busca
    })


@login_required
def detalhe_equipamento_view(request, id):
    equipamento = get_object_or_404(
        Equipamento.objects.select_related('tipo_equipamento', 'grupo', 'departamento', 'predio'),
        id=id
    )

    servicos_config = []
    if equipamento.tipo_equipamento:
        servicos_config = list(
            ServicoTipoEquipamento.objects.filter(
                tipo_equipamento=equipamento.tipo_equipamento,
                ativo=True
            )
            .select_related('tipo_servico', 'periodicidade')
            .prefetch_related('secoes_checklist__itens')
        )

    hoje = timezone.localdate()
    for config in servicos_config:
        ultimo_servico = (
            Servico.objects.filter(
                equipamento=equipamento,
                tipo_servico=config.tipo_servico,
                status='concluido'
            )
            .select_related('realizado_por', 'tipo_servico')
            .order_by('-criado_em')
            .first()
        )

        data_base = ultimo_servico.criado_em.date() if ultimo_servico else equipamento.criado_em.date()
        vencimento = _calcular_proximo_vencimento(data_base, config.periodicidade)
        dias_restantes = (vencimento - hoje).days if vencimento else None

        config.ultimo_servico = ultimo_servico
        config.vencimento = vencimento
        config.vencimento_formatado = vencimento.strftime('%d/%m/%Y') if vencimento else ''
        config.dias_restantes = dias_restantes
        config.dias_restantes_abs = abs(dias_restantes) if dias_restantes is not None else None
        config.vencido = dias_restantes is not None and dias_restantes < 0
        config.proximo = dias_restantes is not None and 0 <= dias_restantes <= 7
        config.checklist_total = ItemChecklist.objects.filter(
            secao__servico_tipo_equipamento=config,
            secao__ativo=True,
            ativo=True
        ).count()

    ultimos_servicos = (
        Servico.objects.filter(equipamento=equipamento, status='concluido')
        .select_related('tipo_servico', 'realizado_por')
        .prefetch_related('respostas')
        .order_by('-criado_em')[:6]
    )

    return render(request, 'core/detalhe_equipamento.html', {
        'equipamento': equipamento,
        'servicos_config': servicos_config,
        'ultimos_servicos': ultimos_servicos,
        'ultima_vistoria': ultimos_servicos[0] if ultimos_servicos else None,
        'total_servicos': equipamento.servicos.filter(status='concluido').count(),
        'tipos_equipamento': TipoEquipamento.objects.filter(ativo=True).order_by('nome'),
        'departamentos': Departamento.objects.filter(ativo=True).order_by('nome'),
        'predios': Predio.objects.filter(ativo=True).order_by('nome'),
    })


@login_required
def editar_equipamento_view(request, id):
    equipamento = get_object_or_404(Equipamento, id=id)

    if request.method == 'POST':
        form = EquipamentoForm(request.POST, request.FILES, instance=equipamento)
        if form.is_valid():
            form.save()
            return redirect('detalhe_equipamento', id=equipamento.id)
    else:
        form = EquipamentoForm(instance=equipamento)

    return render(request, 'core/editar_equipamento.html', {
        'form': form,
        'equipamento': equipamento
    })


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def criar_equipamento_view(request):
    if request.method == 'POST':
        form = EquipamentoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('equipamentos')
    else:
        form = EquipamentoForm()

    return render(request, 'core/criar_equipamento.html', {
        'form': form
    })


@login_required
def minha_conta_view(request):
    user = request.user
    perfil, _ = UsuarioPerfil.objects.get_or_create(user=user)
    usuario_simples = not (user.is_superuser or user.is_staff)
    field_errors = {}

    if request.method == 'POST':
        nome_completo = request.POST.get('nome_completo', '').strip()
        username = request.POST.get('username', user.username).strip()
        email = request.POST.get('email', user.email).strip().lower()
        senha_atual = request.POST.get('senha_atual', '')
        nova_senha = request.POST.get('nova_senha', '')
        confirmar_senha = request.POST.get('confirmar_senha', '')
        foto = request.FILES.get('foto')

        if not nome_completo:
            field_errors['nome_completo'] = 'Informe seu nome.'

        if not username:
            field_errors['username'] = 'Informe o nome de usuário.'
        elif User.objects.exclude(id=user.id).filter(username__iexact=username).exists():
            field_errors['username'] = 'Este nome de usuário já está em uso.'

        if usuario_simples and username != user.username:
            field_errors['username'] = 'Usuário simples não pode alterar o nome de usuário usado no login.'

        if not email:
            field_errors['email'] = 'Informe seu e-mail.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                field_errors['email'] = 'Informe um e-mail válido.'
            else:
                if User.objects.exclude(id=user.id).filter(email__iexact=email).exists():
                    field_errors['email'] = 'Este e-mail já está em uso.'

        if usuario_simples and email != (user.email or '').lower():
            field_errors['email'] = 'Usuário simples não pode alterar o e-mail de acesso.'

        quer_alterar_senha = bool(senha_atual or nova_senha or confirmar_senha)
        if quer_alterar_senha:
            if not senha_atual:
                field_errors['senha_atual'] = 'Informe sua senha atual.'
            elif not user.check_password(senha_atual):
                field_errors['senha_atual'] = 'Senha atual incorreta.'

            if len(nova_senha) < 8:
                field_errors['nova_senha'] = 'A nova senha precisa ter pelo menos 8 caracteres.'
            if nova_senha != confirmar_senha:
                field_errors['confirmar_senha'] = 'As senhas não conferem.'

        if foto:
            extensoes_permitidas = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
            if not foto.name.lower().endswith(extensoes_permitidas):
                field_errors['foto'] = 'Envie uma imagem JPG, PNG, GIF ou WEBP.'
            elif foto.size > 5 * 1024 * 1024:
                field_errors['foto'] = 'A foto deve ter no máximo 5 MB.'

        if not field_errors:
            user.first_name = nome_completo
            user.last_name = ''
            if not usuario_simples:
                user.username = username
                user.email = email
            if quer_alterar_senha:
                user.set_password(nova_senha)
            user.save()

            if foto:
                perfil.foto = foto
                perfil.save()

            if quer_alterar_senha:
                update_session_auth_hash(request, user)

            messages.success(request, 'Sua conta foi atualizada com sucesso.')
            return redirect('minha_conta')

        messages.error(request, 'Confira os campos destacados e tente novamente.')

    nome_exibicao = user.get_full_name() or user.username
    return render(request, 'core/minha_conta.html', {
        'perfil': perfil,
        'nome_exibicao': nome_exibicao,
        'field_errors': field_errors,
        'usuario_simples': usuario_simples,
    })


# VIEWS PARA DEPARTAMENTOS
@login_required
def departamentos_view(request):
    """View para listar departamentos"""
    return render(request, 'core/departamentos.html')


@login_required
@require_http_methods(["GET"])
def api_departamentos_listar(request):
    """API para listar departamentos com filtros e paginação"""
    try:
        departamento_id = request.GET.get('id')
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '').strip()
        predio_id = request.GET.get('predio_id', '').strip()
        
        departamentos_base = Departamento.objects.select_related('predio').all()
        departamentos = departamentos_base

        if departamento_id:
            departamentos = departamentos.filter(id=departamento_id)
        
        if search:
            departamentos = departamentos.filter(
                Q(nome__icontains=search) |
                Q(descricao__icontains=search) |
                Q(localizacao__icontains=search) |
                Q(responsavel__icontains=search) |
                Q(email__icontains=search) |
                Q(predio__nome__icontains=search)
            )

        if status == 'ativo':
            departamentos = departamentos.filter(ativo=True)
        elif status == 'inativo':
            departamentos = departamentos.filter(ativo=False)

        if predio_id:
            departamentos = departamentos.filter(predio_id=predio_id)
        
        if sort == 'asc':
            departamentos = departamentos.order_by('nome')
        else:
            departamentos = departamentos.order_by('-nome')
        
        total = departamentos.count()
        total_ativos = departamentos_base.filter(ativo=True).count()
        total_inativos = departamentos_base.filter(ativo=False).count()
        total_com_predio = departamentos_base.filter(predio__isnull=False).count()
        
        start = (page - 1) * rows
        end = start + rows
        departamentos_paginados = departamentos[start:end]
        
        dados = []
        for depto in departamentos_paginados:
            dados.append({
                'id': depto.id,
                'nome': depto.nome,
                'descricao': depto.descricao or '',
                'localizacao': depto.localizacao or '',
                'responsavel': depto.responsavel or '',
                'email': depto.email or '',
                'telefone': depto.telefone or '',
                'predio_id': depto.predio.id if depto.predio else None,
                'predio_nome': depto.predio.nome if depto.predio else None,
                'status': depto.ativo,
                'criado_em': depto.criado_em.strftime('%Y-%m-%d'),
            })
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_inativos': total_inativos,
            'total_com_predio': total_com_predio,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_departamentos_criar(request):
    """API para criar um novo departamento"""
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        localizacao = data.get('localizacao', '')
        responsavel = data.get('responsavel', '')
        email = data.get('email', '')
        telefone = data.get('telefone', '')
        predio_id = data.get('predio_id')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do departamento é obrigatório'
            }, status=400)
        
        if Departamento.objects.filter(nome=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um departamento com o nome "{nome}"'
            }, status=400)
        
        predio = None
        if predio_id:
            try:
                predio = Predio.objects.get(id=predio_id, ativo=True)
            except Predio.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Prédio não encontrado'
                }, status=400)
        
        departamento = Departamento.objects.create(
            nome=nome,
            descricao=descricao,
            localizacao=localizacao,
            responsavel=responsavel,
            email=email,
            telefone=telefone,
            predio=predio,
            ativo=status
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Departamento "{nome}" criado com sucesso!',
            'data': {
                'id': departamento.id,
                'nome': departamento.nome,
                'descricao': departamento.descricao,
                'status': departamento.ativo,
                'criado_em': departamento.criado_em.strftime('%Y-%m-%d'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_departamentos_editar(request, id):
    """API para editar um departamento"""
    try:
        departamento = get_object_or_404(Departamento, id=id)
        data = json.loads(request.body)
        
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        localizacao = data.get('localizacao', '')
        responsavel = data.get('responsavel', '')
        email = data.get('email', '')
        telefone = data.get('telefone', '')
        predio_id = data.get('predio_id')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do departamento é obrigatório'
            }, status=400)
        
        if Departamento.objects.filter(nome=nome).exclude(id=id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um departamento com o nome "{nome}"'
            }, status=400)

        predio = None
        if predio_id:
            try:
                predio = Predio.objects.get(id=predio_id, ativo=True)
            except Predio.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Prédio não encontrado'
                }, status=400)
        
        departamento.nome = nome
        departamento.descricao = descricao
        departamento.localizacao = localizacao
        departamento.responsavel = responsavel
        departamento.email = email
        departamento.telefone = telefone
        departamento.predio = predio
        departamento.ativo = status
        departamento.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Departamento "{nome}" atualizado com sucesso!',
            'data': {
                'id': departamento.id,
                'nome': departamento.nome,
                'descricao': departamento.descricao,
                'status': departamento.ativo,
                'criado_em': departamento.criado_em.strftime('%Y-%m-%d'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_departamentos_excluir(request, id):
    """API para excluir um departamento"""
    try:
        departamento = get_object_or_404(Departamento, id=id)
        
        # Verificar se tem equipamentos vinculados
        if departamento.equipamentos.count() > 0:
            return JsonResponse({
                'success': False,
                'error': f'Não é possível excluir o departamento "{departamento.nome}" pois ele possui {departamento.equipamentos.count()} equipamento(s) vinculado(s).'
            }, status=400)
        
        nome = departamento.nome
        departamento.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Departamento "{nome}" excluído com sucesso!'
        })
    except Exception as e:
        return _json_exception(e)

# VIEWS PARA TIPOS DE SERVIÇO
@login_required
def tipos_servico_view(request):
    """View para listar tipos de serviço"""
    return render(request, 'core/tipos_servico.html')


@login_required
@require_http_methods(["GET"])
def api_tipos_servico_listar(request):
    """API para listar tipos de serviço com filtros e paginação"""
    try:
        tipo_id = request.GET.get('id')
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '').strip()
        
        tipos_base = TipoServico.objects.prefetch_related('equipamentos_configurados', 'servicos').all()
        tipos = tipos_base

        if tipo_id:
            tipos = tipos.filter(id=tipo_id)
        
        if search:
            tipos = tipos.filter(
                Q(nome__icontains=search) |
                Q(descricao__icontains=search)
            )

        if status == 'ativo':
            tipos = tipos.filter(ativo=True)
        elif status == 'inativo':
            tipos = tipos.filter(ativo=False)
        
        if sort == 'asc':
            tipos = tipos.order_by('nome')
        else:
            tipos = tipos.order_by('-nome')
        
        total = tipos.count()
        total_ativos = tipos_base.filter(ativo=True).count()
        total_inativos = tipos_base.filter(ativo=False).count()
        total_configuracoes = ServicoTipoEquipamento.objects.filter(tipo_servico__isnull=False).count()
        
        start = (page - 1) * rows
        tipos_paginados = tipos[start:start + rows]
        
        dados = []
        for tipo in tipos_paginados:
            dados.append({
                'id': tipo.id,
                'nome': tipo.nome,
                'descricao': tipo.descricao or '',
                'configuracoes': tipo.equipamentos_configurados.count(),
                'servicos': tipo.servicos.count(),
                'status': tipo.ativo,
                'criado_em': tipo.criado_em.strftime('%Y-%m-%d %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_inativos': total_inativos,
            'total_configuracoes': total_configuracoes,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_tipos_servico_criar(request):
    """API para criar um novo tipo de serviço"""
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do tipo de serviço é obrigatório'
            }, status=400)
        
        if TipoServico.objects.filter(nome=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um tipo de serviço com o nome "{nome}"'
            }, status=400)
        
        tipo = TipoServico.objects.create(
            nome=nome,
            descricao=descricao,
            ativo=status
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Tipo de serviço "{nome}" criado com sucesso!',
            'data': {
                'id': tipo.id,
                'nome': tipo.nome,
                'descricao': tipo.descricao,
                'status': tipo.ativo,
                'criado_em': tipo.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_tipos_servico_editar(request, id):
    """API para editar um tipo de serviço"""
    try:
        tipo = get_object_or_404(TipoServico, id=id)
        data = json.loads(request.body)
        
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do tipo de serviço é obrigatório'
            }, status=400)
        
        if TipoServico.objects.filter(nome=nome).exclude(id=id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um tipo de serviço com o nome "{nome}"'
            }, status=400)
        
        tipo.nome = nome
        tipo.descricao = descricao
        tipo.ativo = status
        tipo.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Tipo de serviço "{nome}" atualizado com sucesso!',
            'data': {
                'id': tipo.id,
                'nome': tipo.nome,
                'descricao': tipo.descricao,
                'status': tipo.ativo,
                'criado_em': tipo.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_tipos_servico_excluir(request, id):
    """API para excluir um tipo de serviço"""
    try:
        tipo = get_object_or_404(TipoServico, id=id)
        nome = tipo.nome
        tipo.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Tipo de serviço "{nome}" excluído com sucesso!'
        })
    except Exception as e:
        return _json_exception(e)
    

# VIEWS PARA PERIODICIDADES
@login_required
def periodicidades_view(request):
    """View para listar periodicidades"""
    return render(request, 'core/periodicidades.html')


@login_required
@require_http_methods(["GET"])
def api_periodicidades_listar(request):
    """API para listar periodicidades com filtros e paginação"""
    try:
        periodicidade_id = request.GET.get('id')
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '').strip()
        modo = request.GET.get('modo', '').strip()
        
        periodicidades_base = Periodicidade.objects.prefetch_related('tipos_equipamento', 'servicos_configurados').all()
        periodicidades = periodicidades_base

        if periodicidade_id:
            periodicidades = periodicidades.filter(id=periodicidade_id)
        
        if search:
            periodicidades = periodicidades.filter(
                Q(nome__icontains=search) |
                Q(tipo__icontains=search)
            )

        if status == 'ativo':
            periodicidades = periodicidades.filter(ativo=True)
        elif status == 'inativo':
            periodicidades = periodicidades.filter(ativo=False)

        if modo == 'demanda':
            periodicidades = periodicidades.filter(por_demanda=True)
        elif modo == 'prazo':
            periodicidades = periodicidades.filter(por_demanda=False)
        
        if sort == 'asc':
            periodicidades = periodicidades.order_by('nome')
        else:
            periodicidades = periodicidades.order_by('-nome')
        
        total = periodicidades.count()
        total_ativos = periodicidades_base.filter(ativo=True).count()
        total_por_demanda = periodicidades_base.filter(por_demanda=True).count()
        total_configuracoes = (
            TipoEquipamento.objects.filter(periodicidade__isnull=False).count() +
            ServicoTipoEquipamento.objects.filter(periodicidade__isnull=False).count()
        )
        
        start = (page - 1) * rows
        periodicidades_paginados = periodicidades[start:start + rows]
        
        dados = []
        for period in periodicidades_paginados:
            configuracoes = period.tipos_equipamento.count() + period.servicos_configurados.count()
            dados.append({
                'id': period.id,
                'nome': period.nome,
                'por_demanda': period.por_demanda,
                'valor': period.valor,
                'tipo': period.tipo,
                'tipo_display': period.get_tipo_display() if period.tipo else '',
                'descricao': period.get_descricao_completa(),
                'configuracoes': configuracoes,
                'status': period.ativo,
                'criado_em': period.criado_em.strftime('%Y-%m-%d %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_por_demanda': total_por_demanda,
            'total_configuracoes': total_configuracoes,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_periodicidades_criar(request):
    """API para criar uma nova periodicidade"""
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').strip()
        por_demanda = data.get('por_demanda', False)
        valor = data.get('valor')
        tipo = data.get('tipo', '')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome da periodicidade é obrigatório'
            }, status=400)
        
        if Periodicidade.objects.filter(nome=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe uma periodicidade com o nome "{nome}"'
            }, status=400)
        
        # Validar se não é por demanda, precisa de valor e tipo
        if not por_demanda:
            if not valor or valor <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'O valor é obrigatório e deve ser maior que zero quando não for por demanda'
                }, status=400)
            if not tipo:
                return JsonResponse({
                    'success': False,
                    'error': 'O tipo é obrigatório quando não for por demanda'
                }, status=400)
        
        periodicidade = Periodicidade.objects.create(
            nome=nome,
            por_demanda=por_demanda,
            valor=valor if valor else None,
            tipo=tipo if tipo else None,
            ativo=status
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Periodicidade "{nome}" criada com sucesso!',
            'data': {
                'id': periodicidade.id,
                'nome': periodicidade.nome,
                'por_demanda': periodicidade.por_demanda,
                'valor': periodicidade.valor,
                'tipo': periodicidade.tipo,
                'status': periodicidade.ativo,
                'criado_em': periodicidade.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_periodicidades_editar(request, id):
    """API para editar uma periodicidade"""
    try:
        periodicidade = get_object_or_404(Periodicidade, id=id)
        data = json.loads(request.body)
        
        nome = data.get('nome', '').strip()
        por_demanda = data.get('por_demanda', False)
        valor = data.get('valor')
        tipo = data.get('tipo', '')
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome da periodicidade é obrigatório'
            }, status=400)
        
        if Periodicidade.objects.filter(nome=nome).exclude(id=id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe uma periodicidade com o nome "{nome}"'
            }, status=400)
        
        # Validar se não é por demanda, precisa de valor e tipo
        if not por_demanda:
            if not valor or valor <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'O valor é obrigatório e deve ser maior que zero quando não for por demanda'
                }, status=400)
            if not tipo:
                return JsonResponse({
                    'success': False,
                    'error': 'O tipo é obrigatório quando não for por demanda'
                }, status=400)
        
        periodicidade.nome = nome
        periodicidade.por_demanda = por_demanda
        periodicidade.valor = valor if valor else None
        periodicidade.tipo = tipo if tipo else None
        periodicidade.ativo = status
        periodicidade.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Periodicidade "{nome}" atualizada com sucesso!',
            'data': {
                'id': periodicidade.id,
                'nome': periodicidade.nome,
                'por_demanda': periodicidade.por_demanda,
                'valor': periodicidade.valor,
                'tipo': periodicidade.tipo,
                'status': periodicidade.ativo,
                'criado_em': periodicidade.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_periodicidades_excluir(request, id):
    """API para excluir uma periodicidade"""
    try:
        periodicidade = get_object_or_404(Periodicidade, id=id)
        nome = periodicidade.nome
        periodicidade.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Periodicidade "{nome}" excluída com sucesso!'
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_tipos_equipamento_listar(request):
    try:
        search = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        rows = int(request.GET.get('rows', 10))
        sort = request.GET.get('sort', 'asc')
        grupo_id = request.GET.get('grupo_id', None)
        status = request.GET.get('status', '')

        tipos = TipoEquipamento.objects.select_related('grupo', 'periodicidade').all()

        if search:
            tipos = tipos.filter(
                Q(nome__icontains=search) |
                Q(descricao__icontains=search) |
                Q(grupo__nome__icontains=search) |
                Q(periodicidade__nome__icontains=search)
            )

        if grupo_id:
            tipos = tipos.filter(grupo_id=grupo_id)

        if status == 'ativo':
            tipos = tipos.filter(ativo=True)
        elif status == 'inativo':
            tipos = tipos.filter(ativo=False)

        if sort == 'asc':
            tipos = tipos.order_by('nome')
        else:
            tipos = tipos.order_by('-nome')

        total = tipos.count()
        total_ativos = tipos.filter(ativo=True).count()
        total_inativos = tipos.filter(ativo=False).count()
        total_grupos = tipos.values('grupo_id').distinct().count()
        start = (page - 1) * rows
        end = start + rows
        tipos_paginados = tipos[start:end]

        dados = []
        for tipo in tipos_paginados:
            dados.append({
                'id': tipo.id,
                'nome': tipo.nome,
                'grupo_id': tipo.grupo.id,
                'grupo_nome': tipo.grupo.nome,
                'periodicidade_id': tipo.periodicidade.id if tipo.periodicidade else None,
                'periodicidade_nome': tipo.periodicidade.nome if tipo.periodicidade else None,
                'descricao': tipo.descricao or '',
                'is_extintor': _tipo_equipamento_is_extintor(tipo),
                'status': tipo.ativo,
                'criado_em': tipo.criado_em.strftime('%Y-%m-%d %H:%M'),
            })

        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_inativos': total_inativos,
            'total_grupos': total_grupos,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)



# VIEWS PARA TIPOS DE EQUIPAMENTO
@login_required
def tipos_equipamento_view(request):
    """View para listar tipos de equipamento"""
    return render(request, 'core/tipos_equipamento.html')

    
@login_required
@require_http_methods(["GET"])
def api_grupos_listar_para_select(request):
    """API para listar grupos para o select (apenas ativos)"""
    try:
        grupos = Grupo.objects.filter(ativo=True).order_by('nome')
        dados = [{'id': grupo.id, 'nome': grupo.nome} for grupo in grupos]
        return JsonResponse({
            'success': True,
            'data': dados
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_tipos_equipamento_criar(request):
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').strip()
        grupo_id = data.get('grupo_id')
        periodicidade_id = data.get('periodicidade_id')
        descricao = data.get('descricao', '')
        status = data.get('status', True)

        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do tipo de equipamento é obrigatório'
            }, status=400)

        if not grupo_id:
            return JsonResponse({
                'success': False,
                'error': 'O grupo é obrigatório'
            }, status=400)

        if not periodicidade_id:
            return JsonResponse({
                'success': False,
                'error': 'A periodicidade é obrigatória'
            }, status=400)

        try:
            grupo = Grupo.objects.get(id=grupo_id, ativo=True)
        except Grupo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grupo não encontrado'
            }, status=400)

        try:
            periodicidade = Periodicidade.objects.get(id=periodicidade_id, ativo=True)
        except Periodicidade.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Periodicidade não encontrada'
            }, status=400)

        if TipoEquipamento.objects.filter(nome=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um tipo de equipamento com o nome "{nome}"'
            }, status=400)

        tipo = TipoEquipamento.objects.create(
            nome=nome,
            grupo=grupo,
            periodicidade=periodicidade,
            descricao=descricao,
            ativo=status
        )

        return JsonResponse({
            'success': True,
            'message': f'Tipo de equipamento "{nome}" criado com sucesso!',
            'data': {
                'id': tipo.id,
                'nome': tipo.nome,
                'grupo_id': tipo.grupo.id,
                'grupo_nome': tipo.grupo.nome,
                'periodicidade_id': tipo.periodicidade.id if tipo.periodicidade else None,
                'periodicidade_nome': tipo.periodicidade.nome if tipo.periodicidade else None,
                'descricao': tipo.descricao,
                'status': tipo.ativo,
                'criado_em': tipo.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_tipo_equipamento_info(request, id):
    """API para atualizar informações do tipo equipamento"""
    try:
        data = json.loads(request.body)
        tipo_equipamento = get_object_or_404(TipoEquipamento, id=id)
        
        tipo_equipamento.nome = data.get('nome')
        tipo_equipamento.grupo_id = data.get('grupo_id')
        
        periodicidade_id = data.get('periodicidade_id')
        if periodicidade_id:
            tipo_equipamento.periodicidade_id = periodicidade_id
        else:
            tipo_equipamento.periodicidade = None
            
        tipo_equipamento.descricao = data.get('descricao', '')
        tipo_equipamento.ativo = data.get('status', True)
        tipo_equipamento.save()
        
        return JsonResponse({'success': True, 'message': 'Informações salvas com sucesso!'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
def api_editor_servico_criar(request):
    try:
        data = json.loads(request.body)
        tipo_equipamento_id = data.get('tipo_equipamento_id')
        tipo_servico_id = data.get('tipo_servico_id')
        periodicidade_id = data.get('periodicidade_id')

        if not tipo_equipamento_id or not tipo_servico_id or not periodicidade_id:
            return JsonResponse({
                'success': False,
                'error': 'Tipo de equipamento, Checklist e periodicidade são obrigatórios.'
            }, status=400)

        with transaction.atomic():
            servico = ServicoTipoEquipamento.objects.create(
                tipo_equipamento_id=tipo_equipamento_id,
                tipo_servico_id=tipo_servico_id,
                periodicidade_id=periodicidade_id,
                obrigatorio=data.get('obrigatorio', True),
                vencimento_final_mes=data.get('vencimento_final_mes', False),
                habilitar_assinatura=data.get('habilitar_assinatura', False),
                assinatura_obrigatoria=data.get('assinatura_obrigatoria', False),
                acoes_obrigatorias=data.get('acoes_obrigatorias', False),
                permitir_servicos_massa=data.get('permitir_servicos_massa', False),
                ativo=data.get('ativo', True),
                ordem=data.get('ordem', 0)
            )
            _sync_editor_checklist(servico, data.get('secoes'))

        return JsonResponse({
            'success': True,
            'message': 'Checklist criado com sucesso.',
            'servico': _serialize_editor_servico(servico)
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': e.messages[0]}, status=400)
    except IntegrityError as e:
        return _json_checklist_duplicado(e)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_editor_servico_detalhes(request, id):
    try:
        servico = get_object_or_404(
            ServicoTipoEquipamento.objects.select_related('tipo_servico', 'periodicidade').prefetch_related('secoes_checklist__itens'),
            id=id
        )
        return JsonResponse({'success': True, 'servico': _serialize_editor_servico(servico)})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
def api_editor_servico_editar(request, id):
    try:
        servico = get_object_or_404(ServicoTipoEquipamento, id=id)
        data = json.loads(request.body)

        if not data.get('tipo_servico_id') or not data.get('periodicidade_id'):
            return JsonResponse({
                'success': False,
                'error': 'Checklist e periodicidade são obrigatórios.'
            }, status=400)

        with transaction.atomic():
            servico.tipo_servico_id = data.get('tipo_servico_id')
            servico.periodicidade_id = data.get('periodicidade_id')
            servico.obrigatorio = data.get('obrigatorio', True)
            servico.vencimento_final_mes = data.get('vencimento_final_mes', False)
            servico.habilitar_assinatura = data.get('habilitar_assinatura', False)
            servico.assinatura_obrigatoria = data.get('assinatura_obrigatoria', False)
            servico.acoes_obrigatorias = data.get('acoes_obrigatorias', False)
            servico.permitir_servicos_massa = data.get('permitir_servicos_massa', False)
            servico.ativo = data.get('ativo', servico.ativo)
            servico.ordem = data.get('ordem', 0)
            servico.save()
            _sync_editor_checklist(servico, data.get('secoes'))

        return JsonResponse({
            'success': True,
            'message': 'Checklist atualizado com sucesso.',
            'servico': _serialize_editor_servico(servico)
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': e.messages[0]}, status=400)
    except IntegrityError as e:
        return _json_checklist_duplicado(e)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
def api_editor_servico_excluir(request, id):
    try:
        servico = get_object_or_404(ServicoTipoEquipamento, id=id)
        servico.delete()
        return JsonResponse({'success': True, 'message': 'Checklist excluído com sucesso.'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
def api_editor_checklist_apagar(request, id):
    try:
        servico = get_object_or_404(ServicoTipoEquipamento, id=id)
        servico.secoes_checklist.all().delete()
        return JsonResponse({'success': True, 'message': 'Checklist apagado com sucesso.'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
def api_editor_secao_criar(request):
    try:
        data = json.loads(request.body)
        servico_id = data.get('servico_id')
        nome = (data.get('nome') or '').strip()

        if not servico_id or not nome:
            return JsonResponse({'success': False, 'error': 'Checklist e nome da seção são obrigatórios.'}, status=400)

        secao = SecaoChecklist.objects.create(
            servico_tipo_equipamento_id=servico_id,
            nome=nome,
            descricao=data.get('descricao', ''),
            ordem=data.get('ordem', 0)
        )

        return JsonResponse({'success': True, 'message': 'Seção criada com sucesso.', 'id': secao.id})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
def api_editor_secao_editar(request, id):
    try:
        secao = get_object_or_404(SecaoChecklist, id=id)
        data = json.loads(request.body)
        nome = (data.get('nome') or '').strip()

        if not nome:
            return JsonResponse({'success': False, 'error': 'Nome da seção é obrigatório.'}, status=400)

        secao.nome = nome
        secao.descricao = data.get('descricao', '')
        secao.ordem = data.get('ordem', secao.ordem)
        secao.save()

        return JsonResponse({'success': True, 'message': 'Seção atualizada com sucesso.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
def api_editor_secao_excluir(request, id):
    try:
        secao = get_object_or_404(SecaoChecklist, id=id)
        secao.delete()
        return JsonResponse({'success': True, 'message': 'Seção excluída com sucesso.'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
def api_editor_item_criar(request):
    try:
        data = json.loads(request.body)
        secao_id = data.get('secao_id')
        pergunta = (data.get('pergunta') or '').strip()

        if not secao_id or not pergunta:
            return JsonResponse({'success': False, 'error': 'Seção e pergunta são obrigatórias.'}, status=400)

        item = ItemChecklist.objects.create(
            secao_id=secao_id,
            pergunta=pergunta,
            tipo_resposta=data.get('tipo_resposta', 'sim_nao'),
            detalhamento=data.get('detalhamento', ''),
            ordem=data.get('ordem', 0),
            obrigatorio=data.get('obrigatorio', True)
        )

        return JsonResponse({'success': True, 'message': 'Pergunta criada com sucesso.', 'id': item.id})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
def api_editor_item_editar(request, id):
    try:
        item = get_object_or_404(ItemChecklist, id=id)
        data = json.loads(request.body)
        pergunta = (data.get('pergunta') or '').strip()

        if not pergunta:
            return JsonResponse({'success': False, 'error': 'Pergunta é obrigatória.'}, status=400)

        item.secao_id = data.get('secao_id')
        item.pergunta = pergunta
        item.tipo_resposta = data.get('tipo_resposta', 'sim_nao')
        item.detalhamento = data.get('detalhamento', '')
        item.ordem = data.get('ordem', 0)
        item.obrigatorio = data.get('obrigatorio', True)
        item.save()

        return JsonResponse({'success': True, 'message': 'Pergunta atualizada com sucesso.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
def api_editor_item_excluir(request, id):
    try:
        item = get_object_or_404(ItemChecklist, id=id)
        item.delete()
        return JsonResponse({'success': True, 'message': 'Pergunta excluída com sucesso.'})
    except Exception as e:
        return _json_exception(e)


def _checklist_bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in ('1', 'true', 'on', 'sim', 'yes')


def _checklist_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _serialize_checklist_item(item):
    return {
        'id': item.id,
        'secao_id': item.secao_id,
        'pergunta': item.pergunta,
        'tipo_resposta': item.tipo_resposta,
        'detalhamento': item.detalhamento or '',
        'ordem': item.ordem,
        'obrigatorio': item.obrigatorio,
        'imagem_url': item.imagem_descritiva.url if item.imagem_descritiva else '',
    }


@login_required
@require_http_methods(["GET"])
def api_checklist_item_detalhes(request, id):
    item = get_object_or_404(ItemChecklist.objects.select_related('secao'), id=id)
    return JsonResponse({'success': True, 'item': _serialize_checklist_item(item)})


@login_required
@require_http_methods(["POST"])
def api_checklist_item_criar(request):
    pergunta = (request.POST.get('pergunta') or '').strip()
    if not pergunta:
        return JsonResponse({'success': False, 'error': 'A pergunta é obrigatória.'}, status=400)

    item = ItemChecklist.objects.create(
        secao_id=request.POST.get('secao_id') or None,
        pergunta=pergunta,
        tipo_resposta=request.POST.get('tipo_resposta') or 'sim_nao',
        detalhamento=request.POST.get('detalhamento') or '',
        ordem=_checklist_int(request.POST.get('ordem')),
        obrigatorio=_checklist_bool(request.POST.get('obrigatorio'), True),
        imagem_descritiva=request.FILES.get('imagem_descritiva')
    )
    return JsonResponse({
        'success': True,
        'message': 'Pergunta criada com sucesso.',
        'item': _serialize_checklist_item(item),
    })


@login_required
@require_http_methods(["POST"])
def api_checklist_item_editar(request, id):
    item = get_object_or_404(ItemChecklist, id=id)
    pergunta = (request.POST.get('pergunta') or '').strip()
    if not pergunta:
        return JsonResponse({'success': False, 'error': 'A pergunta é obrigatória.'}, status=400)

    item.secao_id = request.POST.get('secao_id') or None
    item.pergunta = pergunta
    item.tipo_resposta = request.POST.get('tipo_resposta') or 'sim_nao'
    item.detalhamento = request.POST.get('detalhamento') or ''
    item.ordem = _checklist_int(request.POST.get('ordem'))
    item.obrigatorio = _checklist_bool(request.POST.get('obrigatorio'), True)
    if request.FILES.get('imagem_descritiva'):
        item.imagem_descritiva = request.FILES['imagem_descritiva']
    item.save()

    return JsonResponse({
        'success': True,
        'message': 'Pergunta atualizada com sucesso.',
        'item': _serialize_checklist_item(item),
    })


@login_required
@require_http_methods(["DELETE"])
def api_checklist_item_excluir(request, id):
    item = get_object_or_404(ItemChecklist, id=id)
    item.delete()
    return JsonResponse({'success': True, 'message': 'Pergunta excluída com sucesso.'})
    
@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_tipos_equipamento_editar(request, id):
    try:
        tipo = get_object_or_404(TipoEquipamento, id=id)
        data = json.loads(request.body)

        nome = data.get('nome', '').strip()
        grupo_id = data.get('grupo_id')
        periodicidade_id = data.get('periodicidade_id')
        descricao = data.get('descricao', '')
        status = data.get('status', True)

        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do tipo de equipamento é obrigatório'
            }, status=400)

        if not grupo_id:
            return JsonResponse({
                'success': False,
                'error': 'O grupo é obrigatório'
            }, status=400)

        if not periodicidade_id:
            return JsonResponse({
                'success': False,
                'error': 'A periodicidade é obrigatória'
            }, status=400)

        try:
            grupo = Grupo.objects.get(id=grupo_id, ativo=True)
        except Grupo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grupo não encontrado'
            }, status=400)

        try:
            periodicidade = Periodicidade.objects.get(id=periodicidade_id, ativo=True)
        except Periodicidade.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Periodicidade não encontrada'
            }, status=400)

        if TipoEquipamento.objects.filter(nome=nome).exclude(id=id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um tipo de equipamento com o nome "{nome}"'
            }, status=400)

        tipo.nome = nome
        tipo.grupo = grupo
        tipo.periodicidade = periodicidade
        tipo.descricao = descricao
        tipo.ativo = status
        tipo.save()

        return JsonResponse({
            'success': True,
            'message': f'Tipo de equipamento "{nome}" atualizado com sucesso!',
        })
    except Exception as e:
        return _json_exception(e)

# ==================== TIPO DE EQUIPAMENTO + SERVIÇOS + CHECKLIST ====================

@login_required
def detalhe_tipo_equipamento_view(request, id):
    tipo_equipamento = get_object_or_404(
        TipoEquipamento.objects.select_related('grupo', 'periodicidade'),
        id=id
    )

    servicos = ServicoTipoEquipamento.objects.filter(
        tipo_equipamento=tipo_equipamento
    ).select_related(
        'tipo_servico',
        'periodicidade'
    ).prefetch_related(
        'secoes_checklist__itens'
    ).order_by('ordem', 'tipo_servico__nome')

    grupos = Grupo.objects.filter(ativo=True).order_by('nome')
    tipos_servico = TipoServico.objects.filter(ativo=True).order_by('nome')
    periodicidades = Periodicidade.objects.filter(ativo=True).order_by('nome')

    total_secoes = 0
    total_itens = 0
    servicos_obrigatorios = 0
    for servico in servicos:
        secoes = list(servico.secoes_checklist.filter(ativo=True))
        checklist_total = ItemChecklist.objects.filter(
            secao__servico_tipo_equipamento=servico,
            secao__ativo=True,
            ativo=True
        ).count()

        servico.secoes_count = len(secoes)
        servico.checklist_total_itens = checklist_total
        total_secoes += len(secoes)
        total_itens += checklist_total
        if servico.obrigatorio:
            servicos_obrigatorios += 1

    context = {
        'tipo_equipamento': tipo_equipamento,
        'servicos': servicos,
        'grupos': grupos,
        'tipos_servico': tipos_servico,
        'periodicidades': periodicidades,
        'total_servicos_configurados': servicos.count(),
        'total_secoes_checklist': total_secoes,
        'total_itens_checklist': total_itens,
        'servicos_obrigatorios': servicos_obrigatorios,
    }

    return render(request, 'core/editar_tipo_equipamento.html', context)


@login_required
@require_http_methods(["POST"])
def criar_servico_tipo_equipamento_view(request, tipo_id):
    tipo_equipamento = get_object_or_404(TipoEquipamento, id=tipo_id)

    form = ServicoTipoEquipamentoForm(request.POST)
    if form.is_valid():
        servico = form.save(commit=False)
        servico.tipo_equipamento = tipo_equipamento
        servico.save()
        messages.success(request, 'Checklist adicionado com sucesso.')
    else:
        messages.error(request, 'Erro ao adicionar checklist.')

    return redirect('detalhe_tipo_equipamento', id=tipo_id)


@login_required
@require_http_methods(["POST"])
def editar_servico_tipo_equipamento_view(request, id):
    servico = get_object_or_404(ServicoTipoEquipamento, id=id)

    form = ServicoTipoEquipamentoForm(request.POST, instance=servico)
    if form.is_valid():
        form.save()
        messages.success(request, 'Checklist atualizado com sucesso.')
    else:
        messages.error(request, 'Erro ao atualizar checklist.')

    return redirect('detalhe_tipo_equipamento', id=servico.tipo_equipamento.id)


@login_required
@require_http_methods(["POST"])
def excluir_servico_tipo_equipamento_view(request, id):
    servico = get_object_or_404(ServicoTipoEquipamento, id=id)
    tipo_id = servico.tipo_equipamento.id
    servico.delete()
    messages.success(request, 'Checklist excluído com sucesso.')
    return redirect('detalhe_tipo_equipamento', id=tipo_id)


@login_required
@require_http_methods(["POST"])
def criar_secao_checklist_view(request, servico_id):
    servico = get_object_or_404(ServicoTipoEquipamento, id=servico_id)

    form = SecaoChecklistForm(request.POST)
    if form.is_valid():
        secao = form.save(commit=False)
        secao.servico_tipo_equipamento = servico
        secao.save()
        messages.success(request, 'Seção criada com sucesso.')
    else:
        messages.error(request, 'Erro ao criar seção.')

    return redirect('detalhe_tipo_equipamento', id=servico.tipo_equipamento.id)


@login_required
@require_http_methods(["POST"])
def editar_secao_checklist_view(request, id):
    secao = get_object_or_404(SecaoChecklist, id=id)

    form = SecaoChecklistForm(request.POST, instance=secao)
    if form.is_valid():
        form.save()
        messages.success(request, 'Seção atualizada com sucesso.')
    else:
        messages.error(request, 'Erro ao atualizar seção.')

    return redirect('detalhe_tipo_equipamento', id=secao.servico_tipo_equipamento.tipo_equipamento.id)


@login_required
@require_http_methods(["POST"])
def excluir_secao_checklist_view(request, id):
    secao = get_object_or_404(SecaoChecklist, id=id)
    tipo_id = secao.servico_tipo_equipamento.tipo_equipamento.id
    secao.delete()
    messages.success(request, 'Seção excluída com sucesso.')
    return redirect('detalhe_tipo_equipamento', id=tipo_id)


@login_required
@require_http_methods(["POST"])
def criar_item_checklist_view(request, servico_id):
    servico = get_object_or_404(ServicoTipoEquipamento, id=servico_id)

    form = ItemChecklistForm(
        request.POST,
        request.FILES,
        servico_tipo_equipamento=servico
    )
    if form.is_valid():
        form.save()
        messages.success(request, 'Pergunta criada com sucesso.')
    else:
        messages.error(request, 'Erro ao criar pergunta.')

    return redirect('detalhe_tipo_equipamento', id=servico.tipo_equipamento.id)


@login_required
@require_http_methods(["POST"])
def editar_item_checklist_view(request, id):
    item = get_object_or_404(ItemChecklist, id=id)
    servico = item.secao.servico_tipo_equipamento if item.secao else None

    form = ItemChecklistForm(
        request.POST,
        request.FILES,
        instance=item,
        servico_tipo_equipamento=servico
    )
    if form.is_valid():
        form.save()
        messages.success(request, 'Pergunta atualizada com sucesso.')
    else:
        messages.error(request, 'Erro ao atualizar pergunta.')

    return redirect('detalhe_tipo_equipamento', id=servico.tipo_equipamento.id)


@login_required
@require_http_methods(["POST"])
def excluir_item_checklist_view(request, id):
    item = get_object_or_404(ItemChecklist, id=id)

    if not item.secao or not item.secao.servico_tipo_equipamento:
        messages.error(request, 'Item sem vínculo de checklist.')
        return redirect('tipos_equipamento')

    tipo_id = item.secao.servico_tipo_equipamento.tipo_equipamento.id
    item.delete()
    messages.success(request, 'Pergunta excluída com sucesso.')
    return redirect('detalhe_tipo_equipamento', id=tipo_id)

@login_required
@require_http_methods(["GET"])
def periodicidades_para_select(request):
    try:
        periodicidades = Periodicidade.objects.filter(ativo=True).order_by('nome')

        data = [
            {
                'id': periodicidade.id,
                'nome': periodicidade.nome,
                'descricao': f'{periodicidade.tipo} - {periodicidade.valor}' if periodicidade.valor else periodicidade.tipo,
            }
            for periodicidade in periodicidades
        ]

        return JsonResponse({
            'success': True,
            'data': data
        })

    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["GET"])
def api_periodicidades_para_select(request):
    """API para listar periodicidades para o select"""
    try:
        periodicidades = Periodicidade.objects.filter(ativo=True).order_by('nome')
        dados = [{'id': p.id, 'nome': p.nome, 'descricao': p.get_descricao_completa()} for p in periodicidades]
        return JsonResponse({
            'success': True,
            'data': dados
        })
    except IntegrityError as e:
        return _json_integrity_exception(e)
    except Exception as e:
        return _json_exception(e)
    
@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_tipos_equipamento_excluir(request, id):
    """API para excluir um tipo de equipamento"""
    try:
        tipo = get_object_or_404(TipoEquipamento, id=id)
        nome = tipo.nome
        tipo.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Tipo de equipamento "{nome}" excluído com sucesso!'
        })
    except IntegrityError as e:
        return _json_integrity_exception(e)
    except Exception as e:
        return _json_exception(e)
    
# VIEWS PARA PRÉDIOS
@login_required
def predios_view(request):
    """View para listar prédios"""
    return render(request, 'core/predios.html')

@login_required
@require_http_methods(["GET"])
def api_tipo_equipamento_detalhe(request):
    tipo_id = request.GET.get('tipo_id')

    if not tipo_id:
        return JsonResponse({
            'success': False,
            'error': 'tipo_id não informado.'
        }, status=400)

    try:
        tipo = get_object_or_404(
            TipoEquipamento.objects.select_related('grupo', 'periodicidade'),
            id=tipo_id,
            ativo=True
        )

        periodicidade_nome = None
        data_sugerida = None

        if tipo.periodicidade:
            periodicidade_nome = tipo.periodicidade.get_rotulo_inspecao()
            hoje = timezone.localdate()

            if tipo.periodicidade.por_demanda:
                data_sugerida = hoje
            else:
                data_sugerida = _calcular_proximo_vencimento(hoje, tipo.periodicidade)

        servicos = []
        total_itens = 0
        servicos_configurados = (
            ServicoTipoEquipamento.objects
            .filter(tipo_equipamento=tipo, ativo=True)
            .select_related('tipo_servico', 'periodicidade')
            .prefetch_related('secoes_checklist__itens')
            .order_by('ordem', 'tipo_servico__nome')
        )

        for servico in servicos_configurados:
            itens_count = ItemChecklist.objects.filter(
                secao__servico_tipo_equipamento=servico,
                secao__ativo=True,
                ativo=True
            ).count()
            total_itens += itens_count
            servicos.append({
                'id': servico.id,
                'tipo_servico_id': servico.tipo_servico_id,
                'tipo_servico_nome': servico.tipo_servico.nome if servico.tipo_servico else 'Checklist',
                'periodicidade_id': servico.periodicidade_id,
                'periodicidade_nome': servico.periodicidade.get_rotulo_inspecao() if servico.periodicidade else 'Sem periodicidade',
                'obrigatorio': servico.obrigatorio,
                'itens_count': itens_count,
            })

        return JsonResponse({
            'success': True,
            'tipo_equipamento_id': tipo.id,
            'tipo_equipamento': tipo.nome,
            'grupo_id': tipo.grupo_id,
            'grupo_nome': tipo.grupo.nome if tipo.grupo else '',
            'descricao': tipo.descricao or '',
            'is_extintor': _tipo_equipamento_is_extintor(tipo),
            'periodicidade_nome': periodicidade_nome,
            'data_sugerida': _data_iso(data_sugerida),
            'total_servicos': len(servicos),
            'total_itens': total_itens,
            'servicos': servicos,
        })

    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["GET"])
def api_predios_listar(request):
    """API para listar prédios com filtros e paginação"""
    try:
        predio_id = request.GET.get('id')
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'asc')
        status = request.GET.get('status', '').strip()
        
        predios_base = Predio.objects.prefetch_related('departamentos').all()
        predios = predios_base

        if predio_id:
            predios = predios.filter(id=predio_id)
        
        if search:
            predios = predios.filter(
                Q(nome__icontains=search) |
                Q(descricao__icontains=search) |
                Q(endereco__icontains=search)
            )

        if status == 'ativo':
            predios = predios.filter(ativo=True)
        elif status == 'inativo':
            predios = predios.filter(ativo=False)
        
        if sort == 'asc':
            predios = predios.order_by('nome')
        else:
            predios = predios.order_by('-nome')
        
        total = predios.count()
        total_ativos = predios_base.filter(ativo=True).count()
        total_inativos = predios_base.filter(ativo=False).count()
        total_departamentos = Departamento.objects.filter(predio__isnull=False).count()
        
        start = (page - 1) * rows
        end = start + rows
        predios_paginados = predios[start:end]
        
        dados = []
        for predio in predios_paginados:
            dados.append({
                'id': predio.id,
                'nome': predio.nome,
                'descricao': predio.descricao or '',
                'endereco': predio.endereco or '',
                'departamentos': [{'id': d.id, 'nome': d.nome} for d in predio.departamentos.all()],
                'quantidade_departamentos': predio.departamentos.count(),
                'status': predio.ativo,
                'criado_em': predio.criado_em.strftime('%Y-%m-%d %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_ativos': total_ativos,
            'total_inativos': total_inativos,
            'total_departamentos': total_departamentos,
            'page': page,
            'rows': rows,
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_departamentos_para_select(request):
    """API para listar departamentos para o select"""
    try:
        departamentos = Departamento.objects.filter(ativo=True).order_by('nome')
        dados = [{'id': d.id, 'nome': d.nome} for d in departamentos]
        return JsonResponse({
            'success': True,
            'data': dados
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_predios_criar(request):
    """API para criar um novo prédio"""
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').strip()
        descricao = data.get('descricao', '')
        endereco = data.get('endereco', '')
        departamentos_ids = data.get('departamentos', [])
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do prédio é obrigatório'
            }, status=400)
        
        if Predio.objects.filter(nome=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um prédio com o nome "{nome}"'
            }, status=400)
        
        predio = Predio.objects.create(
            nome=nome,
            descricao=descricao,
            endereco=endereco,
            ativo=status
        )
        
        # Adicionar departamentos
        if departamentos_ids:
            departamentos = Departamento.objects.filter(id__in=departamentos_ids)
            predio.departamentos.set(departamentos)
        
        return JsonResponse({
            'success': True,
            'message': f'Prédio "{nome}" criado com sucesso!',
            'data': {
                'id': predio.id,
                'nome': predio.nome,
                'descricao': predio.descricao,
                'endereco': predio.endereco,
                'status': predio.ativo,
                'criado_em': predio.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_predios_editar(request, id):
    """API para editar um prédio"""
    try:
        predio = get_object_or_404(Predio, id=id)
        data = json.loads(request.body)
        
        nome = data.get('nome', '').strip()
        descricao = data.get('descricao', '')
        endereco = data.get('endereco', '')
        departamentos_ids = data.get('departamentos', [])
        status = data.get('status', True)
        
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'O nome do prédio é obrigatório'
            }, status=400)
        
        if Predio.objects.filter(nome=nome).exclude(id=id).exists():
            return JsonResponse({
                'success': False,
                'error': f'Já existe um prédio com o nome "{nome}"'
            }, status=400)
        
        predio.nome = nome
        predio.descricao = descricao
        predio.endereco = endereco
        predio.ativo = status
        predio.save()
        
        # Atualizar departamentos
        if departamentos_ids:
            departamentos = Departamento.objects.filter(id__in=departamentos_ids)
            predio.departamentos.set(departamentos)
        else:
            predio.departamentos.clear()
        
        return JsonResponse({
            'success': True,
            'message': f'Prédio "{nome}" atualizado com sucesso!',
            'data': {
                'id': predio.id,
                'nome': predio.nome,
                'descricao': predio.descricao,
                'endereco': predio.endereco,
                'status': predio.ativo,
                'criado_em': predio.criado_em.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["GET"])
def api_predios_para_select(request):
    """API para listar prédios para o select (apenas ativos)"""
    try:
        predios = Predio.objects.filter(ativo=True).order_by('nome')
        dados = [{'id': predio.id, 'nome': predio.nome} for predio in predios]
        return JsonResponse({
            'success': True,
            'data': dados
        })
    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_predios_excluir(request, id):
    """API para excluir um prédio"""
    try:
        predio = get_object_or_404(Predio, id=id)
        nome = predio.nome
        predio.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Prédio "{nome}" excluído com sucesso!'
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_departamentos_por_predio(request):
    predio_id = request.GET.get('predio_id')

    if not predio_id:
        return JsonResponse({
            'success': False,
            'error': 'predio_id não informado.'
        }, status=400)

    try:
        departamentos = Departamento.objects.filter(
            ativo=True,
            predio_id=predio_id
        ).order_by('nome')

        data = [
            {
                'id': depto.id,
                'nome': depto.nome
            }
            for depto in departamentos
        ]

        return JsonResponse({
            'success': True,
            'data': data
        })

    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_predio_departamentos(request, predio_id):
    """Lista departamentos vinculados ao prédio selecionado."""
    try:
        predio = get_object_or_404(Predio, id=predio_id)
        departamentos = (
            Departamento.objects
            .filter(predio=predio)
            .select_related('predio')
            .order_by('nome')
        )
        data = [_departamento_predio_api_data(departamento) for departamento in departamentos]
        return JsonResponse(data, safe=False)
    except Http404:
        return JsonResponse({'success': False, 'error': 'Prédio não encontrado.'}, status=404)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_departamento_equipamentos(request, departamento_id):
    """Lista equipamentos vinculados ao departamento selecionado."""
    try:
        departamento = get_object_or_404(
            Departamento.objects.select_related('predio'),
            id=departamento_id,
        )
        equipamentos = (
            Equipamento.objects
            .filter(departamento=departamento)
            .select_related('predio', 'departamento')
            .order_by('nome')
        )
        data = [_equipamento_departamento_api_data(equipamento) for equipamento in equipamentos]
        return JsonResponse(data, safe=False)
    except Http404:
        return JsonResponse({'success': False, 'error': 'Departamento não encontrado.'}, status=404)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_navegacao_predios(request):
    """Lista prédios ativos para o fluxo Prédio -> Departamento -> Equipamentos."""
    try:
        busca = (request.GET.get('q') or request.GET.get('search') or '').strip()
        status = request.GET.get('status', '')
        predios = (
            Predio.objects
            .annotate(
                departamentos_count=Count(
                    'departamentos',
                    filter=Q(departamentos__ativo=True),
                    distinct=True,
                ),
                equipamentos_count=Count(
                    'equipamentos',
                    filter=Q(equipamentos__ativo=True),
                    distinct=True,
                ),
            )
            .order_by('nome')
        )
        predios = _aplicar_filtro_status(predios, status, ativo_padrao=True)

        if busca:
            predios = predios.filter(
                Q(nome__icontains=busca) |
                Q(descricao__icontains=busca) |
                Q(endereco__icontains=busca)
            )

        data = [_predio_navegacao_data(predio) for predio in predios]
        return JsonResponse({'success': True, 'data': data, 'predios': data})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_navegacao_departamentos(request, predio_id=None):
    """Lista departamentos vinculados a um prédio."""
    predio_id = predio_id or request.GET.get('predio_id')
    if not predio_id:
        return JsonResponse({
            'success': False,
            'error': 'predio_id não informado.'
        }, status=400)

    try:
        predio = get_object_or_404(Predio, id=predio_id, ativo=True)
        busca = (request.GET.get('q') or request.GET.get('search') or '').strip()
        status = request.GET.get('status', '')
        departamentos = (
            Departamento.objects
            .filter(predio=predio)
            .select_related('predio')
            .annotate(
                equipamentos_count=Count(
                    'equipamentos',
                    filter=Q(equipamentos__ativo=True),
                    distinct=True,
                )
            )
            .order_by('nome')
        )
        departamentos = _aplicar_filtro_status(departamentos, status, ativo_padrao=True)

        if busca:
            departamentos = departamentos.filter(
                Q(nome__icontains=busca) |
                Q(descricao__icontains=busca) |
                Q(localizacao__icontains=busca) |
                Q(responsavel__icontains=busca) |
                Q(email__icontains=busca)
            )

        data = [_departamento_navegacao_data(departamento) for departamento in departamentos]
        return JsonResponse({
            'success': True,
            'predio': _predio_navegacao_data(predio),
            'data': data,
            'departamentos': data,
        })
    except Http404:
        return JsonResponse({'success': False, 'error': 'Prédio não encontrado.'}, status=404)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_navegacao_equipamentos(request, predio_id=None, departamento_id=None):
    """Lista equipamentos vinculados ao prédio e departamento selecionados."""
    predio_id = predio_id or request.GET.get('predio_id')
    departamento_id = departamento_id or request.GET.get('departamento_id')

    if not predio_id:
        return JsonResponse({'success': False, 'error': 'predio_id não informado.'}, status=400)
    if not departamento_id:
        return JsonResponse({'success': False, 'error': 'departamento_id não informado.'}, status=400)

    try:
        predio = get_object_or_404(Predio, id=predio_id, ativo=True)
        departamento = get_object_or_404(Departamento, id=departamento_id, predio=predio, ativo=True)
        busca = (request.GET.get('q') or request.GET.get('search') or '').strip()
        status = request.GET.get('status', '')
        equipamentos = (
            Equipamento.objects
            .filter(predio=predio, departamento=departamento)
            .select_related('tipo_equipamento', 'grupo', 'predio', 'departamento')
            .order_by('nome')
        )
        equipamentos = _aplicar_filtro_status(equipamentos, status, ativo_padrao=True)
        equipamentos = _filtrar_equipamentos_por_busca(equipamentos, busca)

        data = [_equipamento_navegacao_data(request, equipamento) for equipamento in equipamentos]
        return JsonResponse({
            'success': True,
            'predio': _predio_navegacao_data(predio),
            'departamento': _departamento_navegacao_data(departamento),
            'data': data,
            'equipamentos': data,
            'itens': data,
            'total': len(data),
        })
    except Http404:
        return JsonResponse({
            'success': False,
            'error': 'Prédio ou departamento não encontrado.'
        }, status=404)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_navegacao_equipamento_detalhe(request, id):
    """Retorna os detalhes do equipamento selecionado na navegação por prédio."""
    try:
        equipamento = get_object_or_404(
            Equipamento.objects.select_related('tipo_equipamento', 'grupo', 'predio', 'departamento'),
            id=id,
        )
        data = _equipamento_navegacao_data(request, equipamento)
        return JsonResponse({'success': True, 'data': data, 'equipamento': data})
    except Http404:
        return JsonResponse({'success': False, 'error': 'Equipamento não encontrado.'}, status=404)
    except Exception as e:
        return _json_exception(e)

# core/views.py

# ==================== VIEWS PARA SERVIÇOS ====================

@login_required
def servicos_view(request):
    """View para listar serviços"""
    return render(request, 'core/servicos.html')


@login_required
def rascunhos_view(request):
    """View para listar rascunhos de serviços."""
    return render(request, 'core/rascunhos.html')


@login_required
def relatorios_view(request):
    """View para exportar relatórios condensados de serviços."""
    return render(request, 'core/relatorios.html')


@login_required
def calendario_view(request):
    """View para acompanhar revisões previstas e realizadas no mês."""
    return render(request, 'core/calendario.html')


def _calendario_month_bounds(params):
    hoje = timezone.localdate()
    try:
        ano = int(params.get('ano') or hoje.year)
        mes = int(params.get('mes') or hoje.month)
        if mes < 1 or mes > 12:
            raise ValueError
    except (TypeError, ValueError):
        ano, mes = hoje.year, hoje.month

    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return ano, mes, inicio, fim


def _calendario_param(params, nome):
    return (params.get(nome) or '').strip()


def _calendario_nome_usuario(user):
    if not user:
        return ''
    return user.get_full_name() or user.username or user.email


def _calendario_data_iso(data):
    return data.strftime('%Y-%m-%d') if data else ''


def _calendario_local(equipamento):
    partes = []
    if equipamento.predio:
        partes.append(equipamento.predio.nome)
    if equipamento.departamento:
        partes.append(equipamento.departamento.nome)
    if equipamento.local:
        partes.append(equipamento.local)
    return ' · '.join(partes) or '-'


def _calendario_evento_dict(
    *,
    tipo,
    status,
    status_label,
    equipamento,
    tipo_servico,
    data_calendario,
    data_original,
    periodicidade=None,
    servico=None,
    acoes_count=0,
):
    return {
        'id': f"{tipo}-{servico.id if servico else equipamento.id}-{tipo_servico.id if tipo_servico else 'sem'}-{_calendario_data_iso(data_calendario)}",
        'tipo': tipo,
        'status': status,
        'status_label': status_label,
        'data_calendario': _calendario_data_iso(data_calendario),
        'data_original': _calendario_data_iso(data_original),
        'equipamento_id': equipamento.id,
        'equipamento_nome': equipamento.nome,
        'equipamento_numero_serie': equipamento.numero_serie or equipamento.numero_extintor or '',
        'equipamento_descricao': equipamento.descricao or equipamento.observacoes or '',
        'equipamento_ponto_referencia': equipamento.ponto_referencia or '',
        'predio_id': equipamento.predio_id or '',
        'predio_nome': equipamento.predio.nome if equipamento.predio else '',
        'departamento_id': equipamento.departamento_id or '',
        'departamento_nome': equipamento.departamento.nome if equipamento.departamento else '',
        'grupo_id': equipamento.grupo_id or '',
        'tipo_equipamento_nome': equipamento.tipo_equipamento.nome if equipamento.tipo_equipamento else '',
        'grupo_nome': equipamento.grupo.nome if equipamento.grupo else '',
        'tipo_servico_id': tipo_servico.id if tipo_servico else '',
        'tipo_servico_nome': tipo_servico.nome if tipo_servico else 'Serviço',
        'periodicidade': periodicidade.get_rotulo_inspecao() if periodicidade else '',
        'local': _calendario_local(equipamento),
        'realizado_por_nome': _calendario_nome_usuario(servico.realizado_por) if servico else '',
        'servico_id': servico.id if servico else '',
        'acoes_count': acoes_count,
    }


def _calendario_config_lookup(configs):
    lookup = {}
    for config in configs:
        key = (config.tipo_equipamento_id, config.tipo_servico_id)
        lookup.setdefault(key, config)
    return lookup


def _calendario_queryset_equipamentos(params):
    predio_id = _calendario_param(params, 'predio_id')
    departamento_id = _calendario_param(params, 'departamento_id')
    grupo_id = _calendario_param(params, 'grupo_id')
    tipo_equipamento_id = _calendario_param(params, 'tipo_equipamento_id')
    busca = _calendario_param(params, 'busca')

    equipamentos = (
        Equipamento.objects
        .filter(ativo=True)
        .select_related('predio', 'departamento', 'grupo', 'tipo_equipamento')
    )

    if predio_id:
        equipamentos = equipamentos.filter(predio_id=predio_id)
    if departamento_id:
        equipamentos = equipamentos.filter(departamento_id=departamento_id)
    if grupo_id:
        equipamentos = equipamentos.filter(grupo_id=grupo_id)
    if tipo_equipamento_id:
        equipamentos = equipamentos.filter(tipo_equipamento_id=tipo_equipamento_id)
    if busca:
        equipamentos = equipamentos.filter(
            Q(nome__icontains=busca) |
            Q(numero_serie__icontains=busca) |
            Q(local__icontains=busca) |
            Q(predio__nome__icontains=busca) |
            Q(departamento__nome__icontains=busca)
        )

    return equipamentos


def _calendario_queryset_configs(params, tipo_ids):
    tipo_servico_id = _calendario_param(params, 'tipo_servico_id')
    periodicidade_id = _calendario_param(params, 'periodicidade_id')

    configs = (
        ServicoTipoEquipamento.objects
        .filter(
            ativo=True,
            tipo_servico__ativo=True,
            periodicidade__isnull=False,
            periodicidade__por_demanda=False,
            tipo_equipamento_id__in=tipo_ids,
        )
        .select_related('tipo_servico', 'periodicidade', 'tipo_equipamento')
        .order_by('tipo_equipamento_id', 'ordem', 'tipo_servico__nome')
    )

    if tipo_servico_id:
        configs = configs.filter(tipo_servico_id=tipo_servico_id)
    if periodicidade_id:
        configs = configs.filter(periodicidade_id=periodicidade_id)

    return list(configs)


def _calendario_eventos_data(params):
    ano, mes, inicio, fim = _calendario_month_bounds(params)
    hoje = timezone.localdate()
    status_filtro = _calendario_param(params, 'status')
    responsavel_id = _calendario_param(params, 'responsavel_id')
    tipo_servico_id = _calendario_param(params, 'tipo_servico_id')
    periodicidade_id = _calendario_param(params, 'periodicidade_id')
    acoes_filtro = _calendario_param(params, 'acoes')

    equipamentos = list(_calendario_queryset_equipamentos(params))
    equipamento_ids = [equipamento.id for equipamento in equipamentos]
    tipo_ids = sorted({equipamento.tipo_equipamento_id for equipamento in equipamentos if equipamento.tipo_equipamento_id})

    configs = _calendario_queryset_configs(params, tipo_ids) if tipo_ids else []
    configs_por_tipo = {}
    for config in configs:
        configs_por_tipo.setdefault(config.tipo_equipamento_id, []).append(config)
    config_lookup = _calendario_config_lookup(configs)

    eventos = []

    servicos = (
        Servico.objects
        .filter(
            status='concluido',
            equipamento_id__in=equipamento_ids,
            criado_em__date__gte=inicio,
            criado_em__date__lte=fim,
        )
        .select_related(
            'equipamento',
            'equipamento__predio',
            'equipamento__departamento',
            'equipamento__grupo',
            'equipamento__tipo_equipamento',
            'tipo_servico',
            'realizado_por',
        )
        .prefetch_related('acoes_corretivas')
        .order_by('criado_em')
    )

    if tipo_servico_id:
        servicos = servicos.filter(tipo_servico_id=tipo_servico_id)
    if responsavel_id:
        servicos = servicos.filter(realizado_por_id=responsavel_id)

    for servico in servicos:
        config = config_lookup.get((servico.equipamento.tipo_equipamento_id, servico.tipo_servico_id))
        if periodicidade_id and not config:
            continue

        acoes_count = servico.acoes_corretivas.count()
        if acoes_filtro == 'com_acoes' and not acoes_count:
            continue
        if acoes_filtro == 'sem_acoes' and acoes_count:
            continue
        if status_filtro and status_filtro != 'realizada':
            continue

        data_realizacao = timezone.localtime(servico.criado_em).date()
        eventos.append(_calendario_evento_dict(
            tipo='realizada',
            status='realizada',
            status_label='Realizada',
            equipamento=servico.equipamento,
            tipo_servico=servico.tipo_servico,
            data_calendario=data_realizacao,
            data_original=data_realizacao,
            periodicidade=config.periodicidade if config else None,
            servico=servico,
            acoes_count=acoes_count,
        ))

    if not responsavel_id and acoes_filtro != 'com_acoes' and status_filtro != 'realizada':
        servico_tipo_ids = sorted({config.tipo_servico_id for config in configs if config.tipo_servico_id})
        ultimos = {}
        if equipamento_ids and servico_tipo_ids:
            servicos_anteriores = (
                Servico.objects
                .filter(
                    status='concluido',
                    equipamento_id__in=equipamento_ids,
                    tipo_servico_id__in=servico_tipo_ids,
                    criado_em__date__lte=fim,
                )
                .select_related('realizado_por')
                .order_by('equipamento_id', 'tipo_servico_id', '-criado_em')
            )
            for servico in servicos_anteriores:
                key = (servico.equipamento_id, servico.tipo_servico_id)
                if key not in ultimos:
                    ultimos[key] = servico

        for equipamento in equipamentos:
            for config in configs_por_tipo.get(equipamento.tipo_equipamento_id, []):
                ultimo = ultimos.get((equipamento.id, config.tipo_servico_id))
                if ultimo:
                    data_base = timezone.localtime(ultimo.criado_em).date()
                else:
                    data_base = timezone.localtime(equipamento.criado_em).date()

                vencimento = _calcular_proximo_vencimento(data_base, config.periodicidade)
                if not vencimento:
                    continue

                if config.vencimento_final_mes:
                    ultimo_dia = calendar.monthrange(vencimento.year, vencimento.month)[1]
                    vencimento = vencimento.replace(day=ultimo_dia)

                if vencimento > fim:
                    continue

                status = 'vencida' if vencimento < hoje else 'pendente'
                if status_filtro and status_filtro != status:
                    continue

                data_calendario = vencimento if vencimento >= inicio else inicio
                eventos.append(_calendario_evento_dict(
                    tipo='prevista',
                    status=status,
                    status_label='Vencida' if status == 'vencida' else 'Pendente',
                    equipamento=equipamento,
                    tipo_servico=config.tipo_servico,
                    data_calendario=data_calendario,
                    data_original=vencimento,
                    periodicidade=config.periodicidade,
                ))

    eventos.sort(key=lambda item: (item['data_calendario'], item['status'], item['equipamento_nome']))
    resumo = {
        'total': len(eventos),
        'pendentes': sum(1 for item in eventos if item['status'] == 'pendente'),
        'vencidas': sum(1 for item in eventos if item['status'] == 'vencida'),
        'realizadas': sum(1 for item in eventos if item['status'] == 'realizada'),
    }

    return {
        'success': True,
        'ano': ano,
        'mes': mes,
        'inicio': _calendario_data_iso(inicio),
        'fim': _calendario_data_iso(fim),
        'resumo': resumo,
        'eventos': eventos,
    }


@login_required
@require_http_methods(["GET"])
def api_calendario_filtros(request):
    """Retorna as opções usadas nos filtros do calendário."""
    try:
        predio_id = _calendario_param(request.GET, 'predio_id')
        grupo_id = _calendario_param(request.GET, 'grupo_id')
        tipo_equipamento_id = _calendario_param(request.GET, 'tipo_equipamento_id')

        departamentos = Departamento.objects.filter(ativo=True).order_by('nome')
        if predio_id:
            departamentos = departamentos.filter(predio_id=predio_id)

        tipos_equipamento = TipoEquipamento.objects.filter(ativo=True).order_by('nome')
        if grupo_id:
            tipos_equipamento = tipos_equipamento.filter(grupo_id=grupo_id)
        if predio_id:
            tipos_equipamento = tipos_equipamento.filter(equipamentos__predio_id=predio_id).distinct()

        servicos_configurados = (
            ServicoTipoEquipamento.objects
            .filter(ativo=True, tipo_servico__ativo=True)
            .select_related('tipo_servico', 'periodicidade')
        )
        if tipo_equipamento_id:
            servicos_configurados = servicos_configurados.filter(tipo_equipamento_id=tipo_equipamento_id)
        elif grupo_id:
            servicos_configurados = servicos_configurados.filter(tipo_equipamento__grupo_id=grupo_id)

        tipos_servico = []
        vistos_servicos = set()
        periodicidades = []
        vistas_periodicidades = set()
        for config in servicos_configurados.order_by('tipo_servico__nome'):
            if config.tipo_servico_id not in vistos_servicos:
                vistos_servicos.add(config.tipo_servico_id)
                tipos_servico.append({'id': config.tipo_servico_id, 'nome': config.tipo_servico.nome})
            if config.periodicidade_id and config.periodicidade_id not in vistas_periodicidades:
                vistas_periodicidades.add(config.periodicidade_id)
                periodicidades.append({
                    'id': config.periodicidade_id,
                    'nome': config.periodicidade.get_rotulo_inspecao(),
                })

        responsaveis = (
            User.objects
            .filter(servicos_realizados__status='concluido')
            .distinct()
            .order_by('first_name', 'username')
        )

        return JsonResponse({
            'success': True,
            'predios': [{'id': predio.id, 'nome': predio.nome} for predio in Predio.objects.filter(ativo=True).order_by('nome')],
            'departamentos': [{'id': departamento.id, 'nome': departamento.nome} for departamento in departamentos],
            'grupos': [{'id': grupo.id, 'nome': grupo.nome} for grupo in Grupo.objects.filter(ativo=True).order_by('nome')],
            'tipos_equipamento': [{'id': tipo.id, 'nome': tipo.nome} for tipo in tipos_equipamento],
            'tipos_servico': tipos_servico,
            'periodicidades': periodicidades,
            'responsaveis': [{'id': user.id, 'nome': _calendario_nome_usuario(user)} for user in responsaveis],
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_calendario_eventos(request):
    """Lista revisões previstas, vencidas e realizadas para o mês selecionado."""
    try:
        return JsonResponse(_calendario_eventos_data(request.GET))
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def exportar_calendario_dados(request):
    """Exporta os dados atuais do calendário em CSV."""
    dados = _calendario_eventos_data(request.GET)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="calendario_{dados["ano"]}_{str(dados["mes"]).zfill(2)}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Data no calendario',
        'Vencimento/realizacao',
        'Status',
        'Equipamento',
        'Numero de serie',
        'Tipo de equipamento',
        'Grupo',
        'Tipo de servico',
        'Periodicidade',
        'Local',
        'Inspecionado por',
        'Acoes corretivas',
    ])

    for evento in dados['eventos']:
        writer.writerow([
            evento['data_calendario'],
            evento['data_original'],
            evento['status_label'],
            evento['equipamento_nome'],
            evento['equipamento_numero_serie'],
            evento['tipo_equipamento_nome'],
            evento['grupo_nome'],
            evento['tipo_servico_nome'],
            evento['periodicidade'],
            evento['local'],
            evento['realizado_por_nome'],
            evento['acoes_count'],
        ])

    return response


@login_required
@require_http_methods(["GET"])
def api_servicos_listar(request):
    """API para listar serviços com filtros e paginação"""
    try:
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', 1)), 1)
        rows = max(int(request.GET.get('rows', 10)), 1)
        sort = request.GET.get('sort', 'desc')
        site = request.GET.get('site', '').strip()
        data_inicio = request.GET.get('data_inicio', '').strip()
        data_fim = request.GET.get('data_fim', '').strip()
        equipamento_id = request.GET.get('equipamento_id', '').strip()
        status = request.GET.get('status', '').strip()
        
        servicos_base = Servico.objects.select_related('equipamento', 'equipamento__predio', 'tipo_servico', 'realizado_por').all()
        servicos = servicos_base

        if equipamento_id:
            servicos = servicos.filter(equipamento_id=equipamento_id)

        if status:
            servicos = servicos.filter(status=status)
        
        if search:
            servicos = servicos.filter(
                Q(equipamento__nome__icontains=search) |
                Q(equipamento__numero_serie__icontains=search) |
                Q(tipo_servico__nome__icontains=search)
            )

        if site:
            servicos = servicos.filter(
                Q(equipamento__predio__nome__icontains=site) |
                Q(equipamento__local__icontains=site)
            )
        
        if data_inicio:
            servicos = servicos.filter(criado_em__date__gte=data_inicio)
        
        if data_fim:
            servicos = servicos.filter(criado_em__date__lte=data_fim)
        
        if sort == 'asc':
            servicos = servicos.order_by('criado_em')
        else:
            servicos = servicos.order_by('-criado_em')
        
        total = servicos.count()
        total_concluidos = servicos_base.filter(status='concluido').count()
        total_rascunhos = servicos_base.filter(status='rascunho').count()
        total_nao_conformes = servicos_base.filter(respostas__opcao='nao_atende').distinct().count()
        start = (page - 1) * rows
        servicos_paginados = servicos[start:start + rows]
        
        dados = []
        for servico in servicos_paginados:
            total_itens = servico.respostas.count()
            itens_atende = servico.respostas.filter(opcao='atende').count()
            itens_nao_atende = servico.respostas.filter(opcao='nao_atende').count()
            itens_nao_aplica = servico.respostas.filter(opcao='nao_aplica').count()
            dados.append({
                'id': servico.id,
                'data_realizacao': servico.criado_em.strftime('%d/%m/%Y'),
                'equipamento_id': servico.equipamento.id,
                'equipamento_nome': servico.equipamento.nome,
                'equipamento_numero_serie': servico.equipamento.numero_serie or servico.equipamento.numero_extintor,
                'tipo_servico_id': servico.tipo_servico.id if servico.tipo_servico else None,
                'tipo_servico_nome': servico.tipo_servico.nome if servico.tipo_servico else '-',
                'local': servico.equipamento.predio.nome if servico.equipamento.predio else servico.equipamento.local,
                'realizado_por_nome': servico.realizado_por.get_full_name() if servico.realizado_por else '-',
                'has_observacao': bool(servico.observacoes),
                'status': servico.status,
                'status_display': dict(Servico.STATUS_CHOICES).get(servico.status, servico.status),
                'total_itens': total_itens,
                'itens_realizados': itens_atende,
                'itens_atende': itens_atende,
                'itens_nao_atende': itens_nao_atende,
                'itens_nao_aplica': itens_nao_aplica,
                'pontuacao_percentual': float(servico.calcular_pontuacao_percentual()),
                'observacoes': servico.observacoes,
            })
        
        return JsonResponse({
            'success': True,
            'data': dados,
            'total': total,
            'total_concluidos': total_concluidos,
            'total_rascunhos': total_rascunhos,
            'total_nao_conformes': total_nao_conformes,
            'page': page,
            'rows': rows
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_servicos_criar(request):
    """API para criar um novo serviço"""
    try:
        data = json.loads(request.body)
        equipamento_id = data.get('equipamento_id')
        tipo_servico_id = data.get('tipo_servico_id')
        respostas = data.get('respostas', [])
        observacoes = data.get('observacoes', '')
        status = data.get('status', 'concluido')
        rascunho_id = data.get('rascunho_id')
        
        equipamento = get_object_or_404(Equipamento, id=equipamento_id)
        tipo_servico = get_object_or_404(TipoServico, id=tipo_servico_id) if tipo_servico_id else None

        servico = None
        if rascunho_id:
            servico = get_object_or_404(
                Servico,
                id=rascunho_id,
                status='rascunho',
                realizado_por=request.user
            )
        elif status == 'rascunho':
            servico = Servico.objects.filter(
                equipamento=equipamento,
                tipo_servico=tipo_servico,
                status='rascunho',
                realizado_por=request.user
            ).first()

        if servico:
            servico.equipamento = equipamento
            servico.tipo_servico = tipo_servico
            servico.observacoes = observacoes
            servico.status = status
            servico.realizado_por = request.user
            servico.respostas.all().delete()
        else:
            servico = Servico.objects.create(
                equipamento=equipamento,
                tipo_servico=tipo_servico,
                observacoes=observacoes,
                status=status,
                realizado_por=request.user
            )
        
        pontuacao_total = 0
        pontuacao_maxima = 0
        respostas_nao_atendem = []
        
        for resp in respostas:
            item_id = resp.get('item_id')
            opcao = resp.get('opcao')
            obs = resp.get('observacao', '')
            
            item = get_object_or_404(ItemChecklist, id=item_id)
            
            # Calcular pontuação
            if opcao == 'atende':
                pontuacao_total += 1
            pontuacao_maxima += 1
            
            resposta_salva = RespostaChecklist.objects.create(
                servico=servico,
                item_checklist=item,
                opcao=opcao,
                observacao=obs
            )
            if status == 'concluido' and opcao == 'nao_atende':
                respostas_nao_atendem.append(resposta_salva)
        
        servico.pontuacao_total = pontuacao_total
        servico.pontuacao_maxima = pontuacao_maxima
        servico.save()

        for resposta in respostas_nao_atendem:
            notificar_checklist_nao_atende(servico, resposta)

        message = 'Rascunho salvo automaticamente.' if status == 'rascunho' else 'Serviço concluído com sucesso!'
        
        return JsonResponse({'success': True, 'message': message, 'servico_id': servico.id})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_servicos_detalhes(request, id):
    """API para obter detalhes de um serviço"""
    try:
        servico = get_object_or_404(Servico, id=id)
        
        respostas = []
        for resposta in servico.respostas.all():
            foto_url = _arquivo_absoluto_url(request, resposta.fotos)
            respostas.append({
                'id': resposta.id,
                'item_id': resposta.item_checklist_id,
                'pergunta': resposta.item_checklist.pergunta,
                'secao_nome': resposta.item_checklist.secao.nome if resposta.item_checklist.secao else 'Checklist',
                'opcao': resposta.opcao,
                'opcao_display': dict(RespostaChecklist.OPCAO_CHOICES).get(resposta.opcao, '-'),
                'observacao': resposta.observacao,
                'foto': foto_url,
                'foto_url': foto_url,
                'fotos_url': foto_url,
            })

        total_itens = servico.respostas.count()
        itens_atende = servico.respostas.filter(opcao='atende').count()
        itens_nao_atende = servico.respostas.filter(opcao='nao_atende').count()
        itens_nao_aplica = servico.respostas.filter(opcao='nao_aplica').count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': servico.id,
                'equipamento_id': servico.equipamento_id,
                'equipamento_nome': servico.equipamento.nome,
                'equipamento_numero_serie': servico.equipamento.numero_serie or servico.equipamento.numero_extintor,
                'equipamento_vencimentos': _equipamento_vencimentos_data(servico.equipamento),
                'tipo_servico_id': servico.tipo_servico_id,
                'tipo_servico_nome': servico.tipo_servico.nome if servico.tipo_servico else '-',
                'data_realizacao': servico.criado_em.strftime('%d/%m/%Y %H:%M'),
                'realizado_por_nome': (servico.realizado_por.get_full_name() or servico.realizado_por.username) if servico.realizado_por else '-',
                'observacoes': servico.observacoes,
                'total_itens': total_itens,
                'itens_atende': itens_atende,
                'itens_nao_atende': itens_nao_atende,
                'itens_nao_aplica': itens_nao_aplica,
                'pontuacao_percentual': float(servico.calcular_pontuacao_percentual()),
                'respostas': respostas,
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_servicos_rascunho(request):
    """API para verificar se existe rascunho para um equipamento"""
    try:
        equipamento_id = request.GET.get('equipamento_id')
        tipo_servico_id = request.GET.get('tipo_servico_id')
        if not equipamento_id:
            return JsonResponse({'success': True, 'has_rascunho': False})

        rascunhos = Servico.objects.filter(
            equipamento_id=equipamento_id,
            status='rascunho',
            realizado_por=request.user
        )

        if tipo_servico_id:
            rascunhos = rascunhos.filter(tipo_servico_id=tipo_servico_id)

        rascunho = rascunhos.select_related('equipamento', 'tipo_servico').first()
        
        if rascunho:
            total_itens = _total_itens_checklist(rascunho.equipamento, rascunho.tipo_servico)
            total_respostas = rascunho.respostas.count()
            return JsonResponse({
                'success': True,
                'has_rascunho': True,
                'rascunho_id': rascunho.id,
                'tipo_servico_id': rascunho.tipo_servico_id,
                'tipo_servico_nome': rascunho.tipo_servico.nome if rascunho.tipo_servico else '-',
                'data_inicio': rascunho.criado_em.strftime('%d/%m/%Y %H:%M'),
                'total_itens': total_itens,
                'total_respostas': total_respostas,
                'progresso': round((total_respostas / total_itens) * 100) if total_itens else 0
            })
        
        return JsonResponse({'success': True, 'has_rascunho': False})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_servicos_descartar(request, id):
    """API para descartar um rascunho"""
    try:
        servico = get_object_or_404(Servico, id=id, status='rascunho', realizado_por=request.user)
        servico.delete()
        return JsonResponse({'success': True, 'message': 'Rascunho descartado com sucesso!'})
    except Exception as e:
        return _json_exception(e)


def _total_itens_checklist(equipamento, tipo_servico):
    if not equipamento or not equipamento.tipo_equipamento_id or not tipo_servico:
        return 0

    return ItemChecklist.objects.filter(
        secao__servico_tipo_equipamento__tipo_equipamento=equipamento.tipo_equipamento,
        secao__servico_tipo_equipamento__tipo_servico=tipo_servico,
        secao__servico_tipo_equipamento__ativo=True,
        secao__ativo=True,
        ativo=True
    ).count()


@login_required
@require_http_methods(["GET"])
def api_rascunhos_listar(request):
    """API para listar rascunhos de checklist do usuário atual."""
    try:
        rascunhos = (
            Servico.objects
            .filter(status='rascunho', realizado_por=request.user)
            .select_related('equipamento', 'equipamento__predio', 'tipo_servico')
            .prefetch_related('respostas')
            .order_by('-atualizado_em')
        )

        dados = []
        for rascunho in rascunhos:
            total_itens = _total_itens_checklist(rascunho.equipamento, rascunho.tipo_servico)
            total_respostas = rascunho.respostas.count()
            dados.append({
                'id': rascunho.id,
                'equipamento_id': rascunho.equipamento_id,
                'equipamento_nome': rascunho.equipamento.nome,
                'equipamento_numero_serie': rascunho.equipamento.numero_serie or rascunho.equipamento.numero_extintor,
                'tipo_servico_id': rascunho.tipo_servico_id,
                'tipo_servico_nome': rascunho.tipo_servico.nome if rascunho.tipo_servico else '-',
                'local': rascunho.equipamento.predio.nome if rascunho.equipamento.predio else rascunho.equipamento.local,
                'criado_em': rascunho.criado_em.strftime('%d/%m/%Y %H:%M'),
                'atualizado_em': rascunho.atualizado_em.strftime('%d/%m/%Y %H:%M'),
                'total_itens': total_itens,
                'total_respostas': total_respostas,
                'progresso': round((total_respostas / total_itens) * 100) if total_itens else 0,
                'observacoes': rascunho.observacoes or '',
            })

        return JsonResponse({'success': True, 'data': dados, 'total': len(dados)})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_equipamentos_para_servico(request):
    """API para listar equipamentos para seleção de serviço"""
    try:
        search = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        rows = int(request.GET.get('rows', 10))
        grupo_id = request.GET.get('grupo_id', '')
        
        equipamentos = Equipamento.objects.select_related('grupo', 'tipo_equipamento', 'predio').filter(ativo=True)
        
        if search:
            equipamentos = equipamentos.filter(
                Q(nome__icontains=search) |
                Q(numero_serie__icontains=search) |
                Q(local__icontains=search)
            )
        
        if grupo_id:
            equipamentos = equipamentos.filter(grupo_id=grupo_id)
        
        total = equipamentos.count()
        start = (page - 1) * rows
        end = start + rows
        equipamentos_paginados = equipamentos[start:end]
        
        dados = []
        for equip in equipamentos_paginados:
            dados.append({
                'id': equip.id,
                'nome': equip.nome,
                'numero_serie': equip.numero_serie,
                'grupo_nome': equip.grupo.nome if equip.grupo else '-',
                'local': equip.predio.nome if equip.predio else equip.local,
                'tipo_equipamento_id': equip.tipo_equipamento.id if equip.tipo_equipamento else None,
                'possui_vencimento': equip.possui_vencimento,
                'data_vencimento': _data_iso(equip.data_vencimento),
                'data_vencimento_formatada': _data_br(equip.data_vencimento),
                'vencimento_carga': _data_iso(equip.vencimento_carga),
                'vencimento_carga_formatado': _data_br(equip.vencimento_carga),
                'vencimento_teste_hidrostatico': _data_iso(equip.vencimento_teste_hidrostatico),
                'vencimento_teste_hidrostatico_formatado': _data_br(equip.vencimento_teste_hidrostatico),
                'is_extintor': equip.is_extintor(),
            })
        
        return JsonResponse({'success': True, 'data': dados, 'total': total, 'page': page, 'rows': rows})
    except Exception as e:
        return _json_exception(e)


def _relatorios_queryset(params):
    servico_id = params.get('servico_id') or ''
    predio_id = params.get('predio_id') or ''
    tipo_equipamento_id = params.get('tipo_equipamento_id') or ''
    tipo_servico_id = params.get('tipo_servico_id') or ''
    equipamento_id = params.get('equipamento_id') or ''
    data_inicio = params.get('data_inicio') or ''
    data_fim = params.get('data_fim') or ''

    servicos = (
        Servico.objects
        .filter(status='concluido')
        .select_related(
            'equipamento',
            'equipamento__predio',
            'equipamento__tipo_equipamento',
            'tipo_servico',
            'realizado_por'
        )
        .prefetch_related(
            Prefetch(
                'respostas',
                queryset=RespostaChecklist.objects.select_related(
                    'item_checklist',
                    'item_checklist__secao'
                ).order_by(
                    'item_checklist__secao__ordem',
                    'item_checklist__ordem',
                    'id'
                )
            ),
            Prefetch(
                'acoes_corretivas',
                queryset=AcaoCorretiva.objects.select_related('item_checklist').order_by('prazo', 'id')
            )
        )
    )

    if servico_id:
        servicos = servicos.filter(id=servico_id)

    if predio_id:
        servicos = servicos.filter(equipamento__predio_id=predio_id)

    if tipo_equipamento_id:
        servicos = servicos.filter(equipamento__tipo_equipamento_id=tipo_equipamento_id)

    if tipo_servico_id:
        servicos = servicos.filter(tipo_servico_id=tipo_servico_id)

    if equipamento_id:
        servicos = servicos.filter(equipamento_id=equipamento_id)

    if data_inicio:
        servicos = servicos.filter(criado_em__date__gte=data_inicio)

    if data_fim:
        servicos = servicos.filter(criado_em__date__lte=data_fim)

    return servicos.order_by('-criado_em')


def _relatorio_metricas(servicos):
    total_servicos = servicos.count()
    total_equipamentos = servicos.values('equipamento_id').distinct().count()
    total_nao_conformes = servicos.filter(respostas__opcao='nao_atende').distinct().count()
    pontuacoes = [float(servico.calcular_pontuacao_percentual()) for servico in servicos]
    media_pontuacao = round(sum(pontuacoes) / len(pontuacoes), 2) if pontuacoes else 0
    return total_servicos, total_equipamentos, total_nao_conformes, media_pontuacao


def _pdf_escape(value):
    return str(value or '').replace('\r', ' ').replace('\n', ' ').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _wrap_pdf_text(text, max_chars):
    words = str(text or '').split()
    if not words:
        return ['']

    lines = []
    current = ''
    for word in words:
        if len(word) > max_chars:
            if current:
                lines.append(current)
                current = ''
            lines.append(word[:max_chars])
            continue

        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def _pdf_text(commands, text, x, y, size=10, color='0.16 0.18 0.22'):
    commands.append(f"{color} rg")
    commands.append("BT")
    commands.append(f"/F1 {size} Tf")
    commands.append(f"{x} {y} Td")
    commands.append(f"({_pdf_escape(text)}) Tj")
    commands.append("ET")


def _pdf_rect(commands, x, y, width, height, color):
    commands.append(f"{color} rg")
    commands.append(f"{x} {y} {width} {height} re f")


def _pdf_stroke_rect(commands, x, y, width, height, color='0.86 0.89 0.93', line_width=0.8):
    commands.append(f"{color} RG")
    commands.append(f"{line_width} w")
    commands.append(f"{x} {y} {width} {height} re S")


def _pdf_line(commands, x1, y1, x2, y2, color='0.86 0.89 0.93', line_width=0.8):
    commands.append(f"{color} RG")
    commands.append(f"{line_width} w")
    commands.append(f"{x1} {y1} m {x2} {y2} l S")


def _build_report_pdf(title, subtitle, rows):
    styles = {
        'section': {'size': 10, 'height': 28, 'max': 82, 'color': '0.07 0.12 0.18'},
        'subsection': {'size': 10, 'height': 18, 'max': 86, 'color': '0.13 0.15 0.18'},
        'metric': {'size': 9, 'height': 15, 'max': 94, 'color': '0.13 0.15 0.18'},
        'question': {'size': 8, 'height': 13, 'max': 84, 'color': '0.27 0.31 0.37'},
        'muted': {'size': 8, 'height': 13, 'max': 104, 'color': '0.50 0.54 0.60'},
        'body': {'size': 9, 'height': 14, 'max': 96, 'color': '0.25 0.28 0.34'},
    }

    pages = []

    def start_page(page_number):
        commands = []
        _pdf_rect(commands, 0, 0, 595, 842, '0.98 0.99 1')
        _pdf_rect(commands, 0, 778, 595, 64, '0.04 0.12 0.18')
        _pdf_rect(commands, 0, 778, 595, 5, '0.93 0.32 0.09')
        _pdf_text(commands, 'NOTCHFIRE', 40, 814, 15, '1 1 1')
        _pdf_text(commands, title, 40, 796, 10, '0.87 0.92 0.96')
        _pdf_text(commands, subtitle, 330, 807, 8, '0.87 0.92 0.96')
        _pdf_line(commands, 40, 42, 555, 42, '0.84 0.87 0.91', 0.6)
        _pdf_text(commands, 'Relatório gerado automaticamente pelo NotchFire', 40, 25, 7, '0.50 0.54 0.60')
        _pdf_text(commands, f'Página {page_number}', 510, 25, 7, '0.50 0.54 0.60')
        return commands, 744

    commands, y = start_page(1)
    page_number = 1

    def ensure_space(height):
        nonlocal commands, y, page_number
        if y - height < 58:
            pages.append(commands)
            page_number += 1
            commands, y = start_page(page_number)

    def render_card_text(label, value, x, top, width):
        _pdf_text(commands, label.upper(), x, top - 18, 7, '0.47 0.51 0.57')
        lines = _wrap_pdf_text(value, max(18, int(width / 5.4)))
        for line_index, line in enumerate(lines[:2]):
            _pdf_text(commands, line, x, top - 34 - (line_index * 11), 10, '0.08 0.12 0.18')

    for row in rows:
        if isinstance(row, str):
            row = {'kind': 'body', 'text': row}

        kind = row.get('kind', 'body')
        text = row.get('text', '')
        style = styles.get(kind, styles['body'])

        if kind == 'hero':
            ensure_space(92)
            _pdf_rect(commands, 40, y - 74, 515, 74, '1 1 1')
            _pdf_stroke_rect(commands, 40, y - 74, 515, 74, '0.85 0.88 0.92', 0.7)
            _pdf_rect(commands, 40, y - 74, 5, 74, row.get('accent', '0.93 0.32 0.09'))
            _pdf_text(commands, row.get('eyebrow', 'RESUMO EXECUTIVO'), 58, y - 20, 8, '0.47 0.51 0.57')
            _pdf_text(commands, text, 58, y - 42, 18, '0.05 0.12 0.18')
            _pdf_text(commands, row.get('description', ''), 58, y - 60, 9, '0.35 0.39 0.45')
            y -= 92
            continue

        if kind == 'info_grid':
            items = row.get('items', [])
            row_height = 45
            total_height = ((len(items) + 1) // 2) * row_height + 10
            ensure_space(total_height)
            for index, item in enumerate(items):
                col = index % 2
                line = index // 2
                x = 44 + (col * 258)
                top = y - (line * row_height)
                _pdf_rect(commands, x, top - 36, 247, 36, '1 1 1')
                _pdf_stroke_rect(commands, x, top - 36, 247, 36, '0.88 0.91 0.94', 0.5)
                render_card_text(item.get('label', ''), item.get('value', '-'), x + 12, top, 220)
            y -= total_height
            continue

        if kind == 'metric_grid':
            metrics = row.get('metrics', [])
            card_width = 122
            gap = 9
            row_height = 62
            total_height = ((len(metrics) + 3) // 4) * row_height + 8
            ensure_space(total_height)
            for index, metric in enumerate(metrics):
                col = index % 4
                line = index // 4
                x = 40 + (col * (card_width + gap))
                top = y - (line * row_height)
                accent = metric.get('accent', '0.93 0.32 0.09')
                _pdf_rect(commands, x, top - 50, card_width, 50, '1 1 1')
                _pdf_stroke_rect(commands, x, top - 50, card_width, 50, '0.87 0.90 0.94', 0.5)
                _pdf_rect(commands, x, top - 50, 4, 50, accent)
                _pdf_text(commands, metric.get('label', '').upper(), x + 12, top - 17, 7, '0.48 0.52 0.58')
                _pdf_text(commands, metric.get('value', '-'), x + 12, top - 38, 16, '0.06 0.11 0.17')
            y -= total_height
            continue

        if kind == 'service_card':
            facts = row.get('facts', [])
            height = 108 + (max(len(facts) - 3, 0) * 12)
            ensure_space(height + 12)
            x = 40
            _pdf_rect(commands, x, y - height, 515, height, '1 1 1')
            _pdf_stroke_rect(commands, x, y - height, 515, height, '0.85 0.88 0.92', 0.7)
            _pdf_rect(commands, x, y - height, 5, height, row.get('accent', '0.93 0.32 0.09'))
            _pdf_text(commands, row.get('title', 'Serviço'), x + 16, y - 22, 12, '0.06 0.11 0.17')
            _pdf_text(commands, row.get('meta', ''), x + 16, y - 39, 8, '0.47 0.51 0.57')
            score = max(0, min(float(row.get('score', 0)), 100))
            _pdf_text(commands, f"{score:.1f}%", x + 438, y - 23, 16, row.get('score_color', '0.10 0.48 0.29'))
            _pdf_rect(commands, x + 16, y - 61, 483, 7, '0.91 0.93 0.96')
            _pdf_rect(commands, x + 16, y - 61, 483 * (score / 100), 7, row.get('bar_color', '0.10 0.48 0.29'))
            for index, fact in enumerate(facts):
                _pdf_text(commands, fact, x + 16, y - 82 - (index * 12), 8, '0.28 0.32 0.38')
            y -= height + 14
            continue

        if kind == 'question':
            status = row.get('status', '')
            observation = row.get('observation', '')
            wrapped = _wrap_pdf_text(text, style['max'])
            height = 21 + (len(wrapped) * 11) + (13 if observation else 0)
            ensure_space(height)
            status_color = row.get('status_color', '0.47 0.51 0.57')
            _pdf_rect(commands, 50, y - 11, 5, 5, status_color)
            for line_index, line in enumerate(wrapped):
                _pdf_text(commands, line, 62, y - 12 - (line_index * 11), style['size'], style['color'])
            _pdf_text(commands, status, 462, y - 12, 8, status_color)
            if observation:
                _pdf_text(commands, f"Obs.: {observation}", 62, y - 14 - (len(wrapped) * 11), 7, '0.50 0.54 0.60')
            y -= height
            continue

        wrapped = _wrap_pdf_text(text, style['max'])
        block_height = style['height'] * max(len(wrapped), 1)
        if kind == 'section':
            block_height += 10
        elif kind == 'subsection':
            block_height += 4

        ensure_space(block_height)

        if kind == 'section':
            _pdf_rect(commands, 40, y - 11, 515, 25, '0.91 0.94 0.97')
            _pdf_rect(commands, 40, y - 11, 5, 25, '0.93 0.32 0.09')
            _pdf_text(commands, text.upper(), 54, y - 2, style['size'], style['color'])
            y -= block_height
            continue

        if kind == 'subsection':
            _pdf_text(commands, text, 42, y, style['size'], style['color'])
            _pdf_rect(commands, 42, y - 7, 512, 0.6, '0.84 0.87 0.90')
            y -= block_height
            continue

        for line in wrapped:
            _pdf_text(commands, line, 52 if kind in {'question', 'muted'} else 44, y, style['size'], style['color'])
            y -= style['height']

    pages.append(commands)

    objects = []
    page_refs = []

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("")

    font_obj_num = 3 + len(pages) * 2
    for index, page_commands in enumerate(pages):
        page_obj = 3 + index * 2
        content_obj = page_obj + 1
        page_refs.append(f"{page_obj} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> /Contents {content_obj} 0 R >>"
        )

        stream = "\n".join(page_commands)
        objects.append(f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode('latin-1'))
        pdf.extend(obj.encode('latin-1', errors='replace'))
        pdf.extend(b"\nendobj\n")

    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode('latin-1'))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode('latin-1'))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode('latin-1')
    )
    return bytes(pdf)


def _format_datetime_br(value):
    if not value:
        return '-'
    return timezone.localtime(value).strftime('%d/%m/%Y %H:%M')


def _format_date_br(value):
    return value.strftime('%d/%m/%Y') if value else '-'


def _relatorio_pdf_response(relatorio, servicos):
    servicos_lista = list(servicos[:80])
    equipamento_foco = relatorio.equipamento or (servicos_lista[0].equipamento if relatorio.total_equipamentos == 1 and servicos_lista else None)
    periodo = (
        f"{_format_date_br(relatorio.data_inicio)} até {_format_date_br(relatorio.data_fim)}"
        if relatorio.data_inicio or relatorio.data_fim
        else 'Todos os registros'
    )
    escopo = equipamento_foco.nome if equipamento_foco else (relatorio.predio.nome if relatorio.predio else 'Todos os equipamentos')

    def status_visual(opcao):
        if opcao == 'atende':
            return '0.10 0.48 0.29', 'Atende'
        if opcao == 'nao_atende':
            return '0.78 0.17 0.17', 'Não atende'
        if opcao == 'nao_aplica':
            return '0.45 0.49 0.55', 'Não se aplica'
        return '0.85 0.50 0.08', 'Sem resposta'

    def score_visual(valor):
        if valor >= 85:
            return '0.10 0.48 0.29'
        if valor >= 65:
            return '0.85 0.50 0.08'
        return '0.78 0.17 0.17'

    rows = [
        {
            'kind': 'hero',
            'text': escopo,
            'eyebrow': 'Relatório do checklist realizado' if relatorio.servico_id else 'Relatório executivo de inspeção',
            'description': 'Registro detalhado do checklist selecionado.' if relatorio.servico_id else 'Resumo pronto para acompanhamento de chefia, supervisão e auditoria operacional.',
        },
        {
            'kind': 'metric_grid',
            'metrics': [
                {'label': 'Serviços', 'value': str(relatorio.total_servicos), 'accent': '0.06 0.38 0.63'},
                {'label': 'Equipamentos', 'value': str(relatorio.total_equipamentos), 'accent': '0.33 0.24 0.68'},
                {'label': 'Não conformes', 'value': str(relatorio.total_nao_conformes), 'accent': '0.78 0.17 0.17'},
                {'label': 'Pontuação média', 'value': f"{float(relatorio.media_pontuacao):.1f}%", 'accent': score_visual(float(relatorio.media_pontuacao))},
            ],
        },
        {'kind': 'section', 'text': 'Escopo do relatório'},
        {
            'kind': 'info_grid',
            'items': [
                {'label': 'Gerado em', 'value': _format_datetime_br(relatorio.criado_em)},
                {'label': 'Período', 'value': periodo},
                {'label': 'Prédio', 'value': relatorio.predio.nome if relatorio.predio else 'Todos'},
                {'label': 'Equipamento', 'value': equipamento_foco.nome if equipamento_foco else 'Todos'},
                {'label': 'Tipo de equipamento', 'value': relatorio.tipo_equipamento.nome if relatorio.tipo_equipamento else 'Todos'},
                {'label': 'Tipo de serviço', 'value': relatorio.tipo_servico.nome if relatorio.tipo_servico else 'Todos'},
                {'label': 'Checklist', 'value': f"#{relatorio.servico_id}" if relatorio.servico_id else 'Todos'},
            ],
        },
    ]

    if equipamento_foco:
        localizacao_foco = ' / '.join(filter(None, [
            equipamento_foco.predio.nome if equipamento_foco.predio else '',
            equipamento_foco.departamento.nome if equipamento_foco.departamento else '',
            equipamento_foco.local or '',
        ])) or '-'
        rows.extend([
            {'kind': 'section', 'text': 'Ficha do equipamento'},
            {
                'kind': 'info_grid',
                'items': [
                    {'label': 'Nome', 'value': equipamento_foco.nome},
                    {'label': 'Série', 'value': equipamento_foco.numero_serie or equipamento_foco.numero_extintor or '-'},
                    {'label': 'Localização', 'value': localizacao_foco},
                    {'label': 'Marca', 'value': equipamento_foco.marca or '-'},
                    {'label': 'Ponto de referência', 'value': equipamento_foco.ponto_referencia or '-'},
                    {'label': 'Status', 'value': 'Ativo' if equipamento_foco.ativo else 'Inativo'},
                ],
            },
        ])

    rows.append({'kind': 'section', 'text': 'Serviços e checklists respondidos'})

    if not servicos_lista:
        rows.append({'kind': 'muted', 'text': 'Nenhum serviço concluído foi encontrado para os filtros selecionados.'})

    for index, servico in enumerate(servicos_lista, start=1):
        equipamento = servico.equipamento
        respostas = list(servico.respostas.all())
        acoes = list(servico.acoes_corretivas.all())
        atende = sum(1 for resposta in respostas if resposta.opcao == 'atende')
        nao_atende = sum(1 for resposta in respostas if resposta.opcao == 'nao_atende')
        nao_aplica = sum(1 for resposta in respostas if resposta.opcao == 'nao_aplica')
        pontuacao = float(servico.calcular_pontuacao_percentual())
        localizacao = ' / '.join(filter(None, [
            equipamento.predio.nome if equipamento.predio else '',
            equipamento.departamento.nome if equipamento.departamento else '',
            equipamento.local or '',
        ])) or '-'

        rows.append({
            'kind': 'service_card',
            'title': f"{index}. {servico.tipo_servico.nome if servico.tipo_servico else 'Serviço'}",
            'meta': f"{equipamento.nome} | {_format_datetime_br(servico.criado_em)}",
            'score': pontuacao,
            'score_color': score_visual(pontuacao),
            'bar_color': score_visual(pontuacao),
            'accent': score_visual(pontuacao),
            'facts': [
                f"Responsável: {servico.realizado_por.get_full_name() or servico.realizado_por.username if servico.realizado_por else '-'}",
                f"Série: {equipamento.numero_serie or equipamento.numero_extintor or '-'} | Tipo: {equipamento.tipo_equipamento.nome if equipamento.tipo_equipamento else '-'}",
                f"Local: {localizacao}",
                f"Checklist: {atende} atende | {nao_atende} não atende | {nao_aplica} não se aplica | {len(acoes)} ações corretivas",
            ],
        })

        if servico.observacoes:
            rows.append({'kind': 'muted', 'text': f"Observações do serviço: {servico.observacoes}"})

        if respostas:
            secao_atual = None
            for resposta in respostas:
                item = resposta.item_checklist
                secao_nome = item.secao.nome if item.secao else 'Checklist'
                if secao_nome != secao_atual:
                    rows.append({'kind': 'muted', 'text': f"Grupo: {secao_nome}"})
                    secao_atual = secao_nome
                status_color, status = status_visual(resposta.opcao)
                rows.append({
                    'kind': 'question',
                    'text': item.pergunta,
                    'status': status,
                    'status_color': status_color,
                    'observation': resposta.observacao or '',
                })
                if resposta.fotos:
                    rows.append({'kind': 'muted', 'text': f"Foto anexada: {resposta.fotos.name}"})
        else:
            rows.append({'kind': 'muted', 'text': 'Checklist sem respostas registradas.'})

        if acoes:
            rows.append({'kind': 'muted', 'text': 'Ações corretivas vinculadas:'})
            for acao in acoes:
                rows.append({
                    'kind': 'question',
                    'text': f"Prazo {_format_date_br(acao.prazo)} | Responsáveis: {acao.responsaveis} | Problema: {acao.problema} | Ação: {acao.acao}",
                    'status': 'Ação',
                    'status_color': '0.06 0.38 0.63',
                })

    total_servicos = relatorio.total_servicos
    if total_servicos > len(servicos_lista):
        rows.append({'kind': 'section', 'text': 'Observação'})
        rows.append({'kind': 'muted', 'text': f"O relatório detalhou os primeiros {len(servicos_lista)} serviços. Existem mais {total_servicos - len(servicos_lista)} serviços dentro dos filtros."})

    pdf = _build_report_pdf(
        'Relatório Condensado',
        f"{escopo} | {periodo}",
        rows
    )
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{relatorio.arquivo_nome}"'
    return response


@login_required
@require_http_methods(["GET"])
def api_relatorios_filtros(request):
    """Retorna opções para os filtros do relatório condensado."""
    try:
        predio_id = request.GET.get('predio_id') or ''
        tipo_equipamento_id = request.GET.get('tipo_equipamento_id') or ''

        predios = Predio.objects.filter(ativo=True).order_by('nome')

        tipos_query = TipoEquipamento.objects.filter(ativo=True).order_by('nome')
        if predio_id:
            tipos_query = tipos_query.filter(equipamentos__predio_id=predio_id).distinct()

        equipamentos_query = Equipamento.objects.filter(ativo=True).order_by('nome')
        if predio_id:
            equipamentos_query = equipamentos_query.filter(predio_id=predio_id)
        if tipo_equipamento_id:
            equipamentos_query = equipamentos_query.filter(tipo_equipamento_id=tipo_equipamento_id)
        else:
            equipamentos_query = equipamentos_query.none()

        servicos_query = ServicoTipoEquipamento.objects.filter(
            ativo=True,
            tipo_servico__ativo=True
        ).select_related('tipo_servico').order_by('tipo_servico__nome')

        if tipo_equipamento_id:
            servicos_query = servicos_query.filter(tipo_equipamento_id=tipo_equipamento_id)
        else:
            servicos_query = servicos_query.none()

        tipos_servico = []
        vistos = set()
        for config in servicos_query:
            if config.tipo_servico_id in vistos:
                continue
            vistos.add(config.tipo_servico_id)
            tipos_servico.append({
                'id': config.tipo_servico_id,
                'nome': config.tipo_servico.nome,
                'periodicidade': config.periodicidade.get_rotulo_inspecao() if config.periodicidade else '-',
            })

        return JsonResponse({
            'success': True,
            'predios': [{'id': predio.id, 'nome': predio.nome} for predio in predios],
            'tipos_equipamento': [{'id': tipo.id, 'nome': tipo.nome} for tipo in tipos_query],
            'tipos_servico': tipos_servico,
            'equipamentos': [
                {
                    'id': equipamento.id,
                    'nome': f"{equipamento.nome} - {equipamento.numero_serie or equipamento.numero_extintor or 'sem série'}"
                }
                for equipamento in equipamentos_query
            ],
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_relatorios_resumo(request):
    """Resumo rápido para os filtros selecionados."""
    try:
        servicos = _relatorios_queryset(request.GET)
        total_servicos, total_equipamentos, total_nao_conformes, media_pontuacao = _relatorio_metricas(servicos)

        ultimos = []
        for servico in servicos[:5]:
            ultimos.append({
                'id': servico.id,
                'equipamento': servico.equipamento.nome,
                'tipo_servico': servico.tipo_servico.nome if servico.tipo_servico else '-',
                'data': servico.criado_em.strftime('%d/%m/%Y'),
                'pontuacao': float(servico.calcular_pontuacao_percentual()),
            })

        return JsonResponse({
            'success': True,
            'total_servicos': total_servicos,
            'total_equipamentos': total_equipamentos,
            'total_nao_conformes': total_nao_conformes,
            'media_pontuacao': media_pontuacao,
            'ultimos': ultimos,
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def exportar_relatorio_condensado(request):
    """Exporta relatório condensado em PDF e salva histórico."""
    try:
        servicos = _relatorios_queryset(request.GET)
        total_servicos, total_equipamentos, total_nao_conformes, media_pontuacao = _relatorio_metricas(servicos)
        timestamp = timezone.localtime().strftime('%Y%m%d_%H%M%S')
        if request.GET.get('servico_id'):
            prefixo_arquivo = 'relatorio_checklist'
        elif request.GET.get('equipamento_id'):
            prefixo_arquivo = 'relatorio_equipamento'
        else:
            prefixo_arquivo = 'relatorio_condensado'
        relatorio = RelatorioGerado.objects.create(
            tipo='condensado',
            predio_id=request.GET.get('predio_id') or None,
            tipo_equipamento_id=request.GET.get('tipo_equipamento_id') or None,
            tipo_servico_id=request.GET.get('tipo_servico_id') or None,
            equipamento_id=request.GET.get('equipamento_id') or None,
            servico_id=request.GET.get('servico_id') or None,
            data_inicio=parse_date(request.GET.get('data_inicio') or ''),
            data_fim=parse_date(request.GET.get('data_fim') or ''),
            total_servicos=total_servicos,
            total_equipamentos=total_equipamentos,
            total_nao_conformes=total_nao_conformes,
            media_pontuacao=media_pontuacao,
            arquivo_nome=f'{prefixo_arquivo}_{timestamp}.pdf',
            criado_por=request.user,
        )
        return _relatorio_pdf_response(relatorio, servicos)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_relatorios_historico(request):
    """Lista relatórios gerados anteriormente."""
    try:
        relatorios = (
            RelatorioGerado.objects
            .filter(criado_por=request.user)
            .select_related('predio', 'tipo_equipamento', 'tipo_servico', 'equipamento')
            .order_by('-criado_em')[:30]
        )

        dados = []
        for relatorio in relatorios:
            dados.append({
                'id': relatorio.id,
                'tipo': relatorio.get_tipo_display(),
                'predio': relatorio.predio.nome if relatorio.predio else 'Todos',
                'tipo_equipamento': relatorio.tipo_equipamento.nome if relatorio.tipo_equipamento else 'Todos',
                'tipo_servico': relatorio.tipo_servico.nome if relatorio.tipo_servico else 'Todos',
                'equipamento': relatorio.equipamento.nome if relatorio.equipamento else 'Todos',
                'servico_id': relatorio.servico_id or '',
                'periodo': (
                    f"{relatorio.data_inicio.strftime('%d/%m/%Y') if relatorio.data_inicio else '-'} - "
                    f"{relatorio.data_fim.strftime('%d/%m/%Y') if relatorio.data_fim else '-'}"
                ),
                'total_servicos': relatorio.total_servicos,
                'media_pontuacao': float(relatorio.media_pontuacao),
                'criado_em': timezone.localtime(relatorio.criado_em).strftime('%d/%m/%Y %H:%M'),
                'arquivo_nome': relatorio.arquivo_nome,
            })

        return JsonResponse({'success': True, 'data': dados})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def baixar_relatorio_gerado(request, id):
    """Baixa novamente um relatório gerado anteriormente."""
    relatorio = get_object_or_404(RelatorioGerado, id=id, criado_por=request.user)
    params = {
        'predio_id': relatorio.predio_id or '',
        'tipo_equipamento_id': relatorio.tipo_equipamento_id or '',
        'tipo_servico_id': relatorio.tipo_servico_id or '',
        'equipamento_id': relatorio.equipamento_id or '',
        'servico_id': relatorio.servico_id or '',
        'data_inicio': relatorio.data_inicio.isoformat() if relatorio.data_inicio else '',
        'data_fim': relatorio.data_fim.isoformat() if relatorio.data_fim else '',
    }
    servicos = _relatorios_queryset(params)
    return _relatorio_pdf_response(relatorio, servicos)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_servicos_atualizar(request, id):
    """API para atualizar um serviço existente (rascunho)"""
    try:
        filtros = {'id': id}
        if not (request.user.is_superuser or request.user.is_staff):
            filtros.update({'status': 'rascunho', 'realizado_por': request.user})

        servico = get_object_or_404(Servico, **filtros)
        data = json.loads(request.body)
        
        respostas = data.get('respostas', [])
        observacoes = data.get('observacoes', '')
        status = data.get('status', 'rascunho')

        if not (request.user.is_superuser or request.user.is_staff) and status != 'rascunho':
            return JsonResponse({
                'success': False,
                'error': 'Usuário comum só pode criar serviço ou manter o próprio rascunho.'
            }, status=403)
        
        servico.observacoes = observacoes
        servico.status = status
        servico.save()
        
        # Atualizar respostas existentes ou criar novas
        respostas_nao_atendem = []
        for resp in respostas:
            item_id = resp.get('item_id')
            opcao = resp.get('opcao')
            obs = resp.get('observacao', '')
            
            resposta, created = RespostaChecklist.objects.update_or_create(
                servico=servico,
                item_checklist_id=item_id,
                defaults={
                    'opcao': opcao,
                    'observacao': obs
                }
            )
            if status == 'concluido' and opcao == 'nao_atende':
                respostas_nao_atendem.append(resposta)
        
        # Calcular pontuação
        pontuacao_total = 0
        pontuacao_maxima = 0
        
        for resposta in servico.respostas.all():
            if resposta.opcao == 'atende':
                pontuacao_total += 1
            pontuacao_maxima += 1
        
        servico.pontuacao_total = pontuacao_total
        servico.pontuacao_maxima = pontuacao_maxima
        servico.save()

        for resposta in respostas_nao_atendem:
            notificar_checklist_nao_atende(servico, resposta)
        
        return JsonResponse({'success': True, 'message': 'Rascunho atualizado com sucesso!'})
    except Http404:
        return JsonResponse({'success': False, 'error': 'Rascunho não encontrado.'}, status=404)
    except Exception as e:
        return _json_exception(e)

@login_required
@require_http_methods(["GET"])
def api_equipamento_detalhes(request, id):
    """API para obter detalhes de um equipamento"""
    try:
        equipamento = get_object_or_404(
            Equipamento.objects.select_related('tipo_equipamento', 'grupo', 'departamento', 'predio'),
            id=id,
        )
        return JsonResponse({
            'success': True,
            'data': _equipamento_navegacao_data(request, equipamento),
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
def api_equipamento_editar_detalhe(request, id):
    """API para editar os campos principais do detalhe do equipamento."""
    try:
        equipamento = get_object_or_404(Equipamento, id=id)
        data = json.loads(request.body)

        numero_serie = (data.get('numero_serie') or '').strip() or None
        if numero_serie:
            existe_numero = Equipamento.objects.filter(numero_serie=numero_serie).exclude(id=equipamento.id).exists()
            if existe_numero:
                return JsonResponse({'success': False, 'error': 'Já existe um equipamento com este número de série.'}, status=400)

        tipo_equipamento_id = data.get('tipo_equipamento_id') or None
        departamento_id = data.get('departamento_id') or None
        predio_id = data.get('predio_id') or None

        if 'local' in data:
            equipamento.local = (data.get('local') or '').strip() or None
        equipamento.numero_serie = numero_serie
        equipamento.numero_extintor = numero_serie
        equipamento.marca = (data.get('marca') or '').strip() or None
        equipamento.ponto_referencia = (data.get('ponto_referencia') or '').strip() or None
        equipamento.descricao = (data.get('descricao') or '').strip() or None
        equipamento.data_fabricacao = data.get('data_fabricacao') or None
        if 'possui_vencimento' in data:
            equipamento.possui_vencimento = bool(data.get('possui_vencimento'))
        if 'data_vencimento' in data:
            equipamento.data_vencimento = data.get('data_vencimento') or None
        if 'vencimento_carga' in data:
            equipamento.vencimento_carga = data.get('vencimento_carga') or None
        if 'vencimento_teste_hidrostatico' in data:
            equipamento.vencimento_teste_hidrostatico = data.get('vencimento_teste_hidrostatico') or None
        equipamento.tipo_equipamento = get_object_or_404(TipoEquipamento, id=tipo_equipamento_id) if tipo_equipamento_id else None
        equipamento.grupo = equipamento.tipo_equipamento.grupo if equipamento.tipo_equipamento else None
        equipamento.departamento = get_object_or_404(Departamento, id=departamento_id) if departamento_id else None
        equipamento.predio = get_object_or_404(Predio, id=predio_id) if predio_id else None
        equipamento.save()

        return JsonResponse({'success': True, 'message': 'Equipamento atualizado com sucesso.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
def api_equipamento_toggle_ativo(request, id):
    """API para ativar/inativar um equipamento."""
    try:
        equipamento = get_object_or_404(Equipamento, id=id)
        equipamento.ativo = not equipamento.ativo
        equipamento.save(update_fields=['ativo', 'atualizado_em'])
        return JsonResponse({
            'success': True,
            'ativo': equipamento.ativo,
            'message': 'Equipamento ativado com sucesso.' if equipamento.ativo else 'Equipamento inativado com sucesso.'
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
def api_equipamento_upload_foto(request, id):
    """API para atualizar a foto do equipamento."""
    try:
        equipamento = get_object_or_404(Equipamento, id=id)
        foto = request.FILES.get('foto')
        if not foto:
            return JsonResponse({'success': False, 'error': 'Selecione uma imagem para enviar.'}, status=400)

        equipamento.foto = foto
        equipamento.save(update_fields=['foto', 'atualizado_em'])
        return JsonResponse({
            'success': True,
            'foto_url': equipamento.foto.url,
            'message': 'Foto atualizada com sucesso.'
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
def api_equipamento_excluir(request, id):
    """API para excluir um equipamento."""
    try:
        equipamento = get_object_or_404(Equipamento, id=id)
        equipamento.delete()
        return JsonResponse({'success': True, 'message': 'Equipamento excluído com sucesso.'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_tipos_servico_para_equipamento(request):
    """API para listar tipos de serviço disponíveis para um equipamento"""
    try:
        equipamento_id = request.GET.get('equipamento_id')
        if not equipamento_id:
            return JsonResponse({'success': True, 'data': []})
        
        equipamento = get_object_or_404(Equipamento, id=equipamento_id)
        
        # Buscar serviços configurados para o tipo de equipamento
        servicos_config = ServicoTipoEquipamento.objects.filter(
            tipo_equipamento=equipamento.tipo_equipamento,
            ativo=True
        ).select_related('tipo_servico', 'periodicidade')
        
        dados = []
        for servico in servicos_config:
            dados.append({
                'id': servico.tipo_servico.id,
                'nome': servico.tipo_servico.nome,
                'descricao': servico.tipo_servico.descricao,
                'periodicidade_nome': servico.periodicidade.get_rotulo_inspecao() if servico.periodicidade else '-',
                'obrigatorio': servico.obrigatorio,
            })
        
        return JsonResponse({'success': True, 'data': dados})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_checklist_itens_por_tipo(request):
    try:
        tipo_equipamento_id = request.GET.get('tipo_equipamento_id')
        tipo_servico_id = request.GET.get('tipo_servico_id')
        if not tipo_equipamento_id:
            return JsonResponse({'success': True, 'data': []})

        tipo_equipamento = get_object_or_404(TipoEquipamento, id=tipo_equipamento_id)

        itens = []
        servicos = ServicoTipoEquipamento.objects.filter(
            tipo_equipamento=tipo_equipamento,
            ativo=True
        ).select_related('tipo_servico', 'periodicidade').prefetch_related('secoes_checklist__itens')

        if tipo_servico_id:
            servicos = servicos.filter(tipo_servico_id=tipo_servico_id)

        tipo_servico_nome = ''

        for servico in servicos:
            if servico.tipo_servico and not tipo_servico_nome:
                tipo_servico_nome = servico.tipo_servico.nome

            for secao in servico.secoes_checklist.filter(ativo=True):
                for item in secao.itens.filter(ativo=True):
                    itens.append({
                        'id': item.id,
                        'pergunta': item.pergunta,
                        'tipo_resposta': item.tipo_resposta,
                        'obrigatorio': item.obrigatorio,
                        'ordem': item.ordem,
                        'secao_nome': secao.nome,
                        'servico_nome': servico.tipo_servico.nome if servico.tipo_servico else '-',
                        'periodicidade_nome': servico.periodicidade.get_rotulo_inspecao() if servico.periodicidade else '-',
                    })

        return JsonResponse({
            'success': True,
            'data': itens,
            'itens': itens,
            'tipo_servico_nome': tipo_servico_nome or 'Checklist',
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_acoes_corretivas_criar(request):
    """API para criar uma ação corretiva"""
    try:
        servico_id = request.POST.get('servico_id')
        item_checklist_id = request.POST.get('item_checklist_id')
        problema = request.POST.get('problema')
        acao = request.POST.get('acao')
        responsaveis = request.POST.get('responsaveis')
        prazo = request.POST.get('prazo')
        anexos = request.FILES.get('anexos')
        
        if not all([problema, acao, responsaveis, prazo]):
            return JsonResponse({'success': False, 'error': 'Preencha todos os campos obrigatórios!'}, status=400)
        
        acao_corretiva = AcaoCorretiva.objects.create(
            servico_id=servico_id if servico_id else None,
            item_checklist_id=item_checklist_id,
            problema=problema,
            acao=acao,
            responsaveis=responsaveis,
            prazo=prazo,
            anexos=anexos
        )
        
        return JsonResponse({'success': True, 'message': 'Ação cadastrada com sucesso!', 'id': acao_corretiva.id})
    except Exception as e:
        return _json_exception(e)
        
        return JsonResponse({'success': True, 'message': 'Ação cadastrada com sucesso!', 'id': acao_corretiva.id})
    except Exception as e:
        return _json_exception(e)


# ==================== VIEWS PARA EDITOR DE TIPO DE EQUIPAMENTO ====================

@login_required
def editor_tipo_equipamento_view(request, id):
    """View para editar tipo de equipamento com abas"""
    tipo_equipamento = get_object_or_404(TipoEquipamento, id=id)
    grupos = Grupo.objects.filter(ativo=True)
    tipos_servico = TipoServico.objects.filter(ativo=True)
    periodicidades = Periodicidade.objects.filter(ativo=True)
    servicos_configurados = ServicoTipoEquipamento.objects.filter(tipo_equipamento=tipo_equipamento)
    secoes_checklist = SecaoChecklist.objects.filter(tipo_equipamento=tipo_equipamento, ativo=True)
    
    return render(request, 'core/editor_tipo_equipamento.html', {
        'tipo_equipamento': tipo_equipamento,
        'grupos': grupos,
        'tipos_servico': tipos_servico,
        'periodicidades': periodicidades,
        'servicos_configurados': servicos_configurados,
        'secoes_checklist': secoes_checklist,
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_tipo_equipamento_servico_criar(request, tipo_id):
    """API para criar checklist para um tipo de equipamento"""
    try:
        data = json.loads(request.body)
        tipo_equipamento = get_object_or_404(TipoEquipamento, id=tipo_id)
        
        servico = ServicoTipoEquipamento.objects.create(
            tipo_equipamento=tipo_equipamento,
            tipo_servico_id=data.get('tipo_servico_id'),
            periodicidade_id=data.get('periodicidade_id'),
            obrigatorio=data.get('obrigatorio', True),
            vencimento_final_mes=data.get('vencimento_final_mes', False),
            habilitar_assinatura=data.get('habilitar_assinatura', False),
            assinatura_obrigatoria=data.get('assinatura_obrigatoria', False),
            acoes_obrigatorias=data.get('acoes_obrigatorias', False),
            permitir_servicos_massa=data.get('permitir_servicos_massa', False),
            site=data.get('site', ''),
            ordem=data.get('ordem', 0)
        )
        
        return JsonResponse({'success': True, 'message': 'Checklist adicionado com sucesso!', 'id': servico.id})
    except IntegrityError as e:
        return _json_checklist_duplicado(e)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_tipo_equipamento_servico_detalhes(request, tipo_id, id):
    """API para obter detalhes de um checklist configurado"""
    try:
        servico = get_object_or_404(ServicoTipoEquipamento, id=id, tipo_equipamento_id=tipo_id)
        return JsonResponse({
            'success': True,
            'servico': {
                'id': servico.id,
                'tipo_servico_id': servico.tipo_servico_id,
                'periodicidade_id': servico.periodicidade_id,
                'obrigatorio': servico.obrigatorio,
                'vencimento_final_mes': servico.vencimento_final_mes,
                'habilitar_assinatura': servico.habilitar_assinatura,
                'assinatura_obrigatoria': servico.assinatura_obrigatoria,
                'acoes_obrigatorias': servico.acoes_obrigatorias,
                'permitir_servicos_massa': servico.permitir_servicos_massa,
                'site': servico.site,
                'ordem': servico.ordem,
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_tipo_equipamento_servico_editar(request, tipo_id, id):
    """API para editar um checklist configurado"""
    try:
        servico = get_object_or_404(ServicoTipoEquipamento, id=id, tipo_equipamento_id=tipo_id)
        data = json.loads(request.body)
        
        servico.tipo_servico_id = data.get('tipo_servico_id')
        servico.periodicidade_id = data.get('periodicidade_id')
        servico.obrigatorio = data.get('obrigatorio', True)
        servico.vencimento_final_mes = data.get('vencimento_final_mes', False)
        servico.habilitar_assinatura = data.get('habilitar_assinatura', False)
        servico.assinatura_obrigatoria = data.get('assinatura_obrigatoria', False)
        servico.acoes_obrigatorias = data.get('acoes_obrigatorias', False)
        servico.permitir_servicos_massa = data.get('permitir_servicos_massa', False)
        servico.site = data.get('site', '')
        servico.ordem = data.get('ordem', 0)
        servico.save()
        
        return JsonResponse({'success': True, 'message': 'Checklist atualizado com sucesso!'})
    except IntegrityError as e:
        return _json_checklist_duplicado(e)
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_tipo_equipamento_servico_excluir(request, tipo_id, id):
    """API para excluir um checklist configurado"""
    try:
        servico = get_object_or_404(ServicoTipoEquipamento, id=id, tipo_equipamento_id=tipo_id)
        servico.delete()
        return JsonResponse({'success': True, 'message': 'Checklist removido com sucesso!'})
    except Exception as e:
        return _json_exception(e)


# ==================== SEÇÕES DO CHECKLIST ====================

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_tipo_equipamento_secao_criar(request, tipo_id):
    """API para criar seção no checklist"""
    try:
        data = json.loads(request.body)
        tipo_equipamento = get_object_or_404(TipoEquipamento, id=tipo_id)
        
        secao = SecaoChecklist.objects.create(
            tipo_equipamento=tipo_equipamento,
            nome=data.get('nome'),
            descricao=data.get('descricao', ''),
            ordem=data.get('ordem', 0)
        )
        
        return JsonResponse({'success': True, 'message': 'Seção criada com sucesso!', 'id': secao.id})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_tipo_equipamento_secao_detalhes(request, tipo_id, id):
    """API para obter detalhes de uma seção"""
    try:
        secao = get_object_or_404(SecaoChecklist, id=id, tipo_equipamento_id=tipo_id)
        return JsonResponse({
            'success': True,
            'secao': {
                'id': secao.id,
                'nome': secao.nome,
                'descricao': secao.descricao,
                'ordem': secao.ordem,
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_tipo_equipamento_secao_editar(request, tipo_id, id):
    """API para editar uma seção"""
    try:
        secao = get_object_or_404(SecaoChecklist, id=id, tipo_equipamento_id=tipo_id)
        data = json.loads(request.body)
        
        secao.nome = data.get('nome')
        secao.descricao = data.get('descricao', '')
        secao.ordem = data.get('ordem', 0)
        secao.save()
        
        return JsonResponse({'success': True, 'message': 'Seção atualizada com sucesso!'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_tipo_equipamento_secao_excluir(request, tipo_id, id):
    """API para excluir uma seção"""
    try:
        secao = get_object_or_404(SecaoChecklist, id=id, tipo_equipamento_id=tipo_id)
        secao.delete()
        return JsonResponse({'success': True, 'message': 'Seção excluída com sucesso!'})
    except Exception as e:
        return _json_exception(e)


# ==================== ITENS DO CHECKLIST ====================

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_tipo_equipamento_item_criar(request, tipo_id):
    """API para criar item no checklist"""
    try:
        data = json.loads(request.body)
        
        item = ItemChecklist.objects.create(
            secao_id=data.get('secao_id'),
            pergunta=data.get('pergunta'),
            tipo_resposta=data.get('tipo_resposta', 'sim_nao'),
            detalhamento=data.get('detalhamento', ''),
            ordem=data.get('ordem', 0),
            obrigatorio=data.get('obrigatorio', True)
        )
        
        return JsonResponse({'success': True, 'message': 'Item criado com sucesso!', 'id': item.id})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["GET"])
def api_tipo_equipamento_item_detalhes(request, tipo_id, id):
    """API para obter detalhes de um item"""
    try:
        item = get_object_or_404(ItemChecklist, id=id)
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'secao_id': item.secao_id,
                'pergunta': item.pergunta,
                'tipo_resposta': item.tipo_resposta,
                'detalhamento': item.detalhamento,
                'ordem': item.ordem,
                'obrigatorio': item.obrigatorio,
            }
        })
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def api_tipo_equipamento_item_editar(request, tipo_id, id):
    """API para editar um item"""
    try:
        item = get_object_or_404(ItemChecklist, id=id)
        data = json.loads(request.body)
        
        item.secao_id = data.get('secao_id')
        item.pergunta = data.get('pergunta')
        item.tipo_resposta = data.get('tipo_resposta', 'sim_nao')
        item.detalhamento = data.get('detalhamento', '')
        item.ordem = data.get('ordem', 0)
        item.obrigatorio = data.get('obrigatorio', True)
        item.save()
        
        return JsonResponse({'success': True, 'message': 'Item atualizado com sucesso!'})
    except Exception as e:
        return _json_exception(e)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_tipo_equipamento_item_excluir(request, tipo_id, id):
    """API para excluir um item"""
    try:
        item = get_object_or_404(ItemChecklist, id=id)
        item.delete()
        return JsonResponse({'success': True, 'message': 'Item excluído com sucesso!'})
    except Exception as e:
        return _json_exception(e)

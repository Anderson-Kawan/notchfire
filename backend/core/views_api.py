import json
import re
from urllib.parse import parse_qs, urlparse

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from .models import AcaoCorretiva, AlertaChecklist, Departamento, Equipamento, ItemChecklist, Notificacao, Predio, RespostaChecklist, Servico, ServicoTipoEquipamento, TipoEquipamento, TipoServico
from .notifications import notificar_checklist_nao_atende
from .serializers import EquipamentoSerializer
from .tenancy import activate_empresa, deactivate_empresa, resolve_empresa_ativa
from .views import _calendario_eventos_data, _serializar_usuario


class EmpresaAtivaAPIMixin:
    _empresa_token = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._empresa_token = activate_empresa(request)

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            return super().finalize_response(request, response, *args, **kwargs)
        finally:
            if self._empresa_token is not None:
                deactivate_empresa(self._empresa_token)
                self._empresa_token = None


def _empresa_api_data(empresa):
    if not empresa:
        return None
    return {
        'id': empresa.id,
        'nome': empresa.nome,
        'slug': empresa.slug,
    }


def _usuario_api_data(request, user):
    data = _serializar_usuario(user)
    if data.get('foto_url'):
        data['foto_url'] = request.build_absolute_uri(data['foto_url'])
    return data


def _absolute_media_url(request, field):
    if not field:
        return ''
    try:
        return request.build_absolute_uri(field.url)
    except ValueError:
        return ''


def _date_iso(value):
    return value.isoformat() if value else ''


def _equipamento_api_data(request, equipamento):
    return {
        'id': equipamento.id,
        'nome': equipamento.nome,
        'numero_serie': equipamento.numero_serie or equipamento.numero_extintor or '',
        'marca': equipamento.marca or '',
        'local': equipamento.predio.nome if equipamento.predio else (equipamento.local or ''),
        'ponto_referencia': equipamento.ponto_referencia or '',
        'tipo_equipamento_id': equipamento.tipo_equipamento_id,
        'tipo_equipamento_nome': equipamento.tipo_equipamento.nome if equipamento.tipo_equipamento else '',
        'grupo_nome': equipamento.grupo.nome if equipamento.grupo else '',
        'possui_vencimento': equipamento.possui_vencimento,
        'data_vencimento': _date_iso(equipamento.data_vencimento),
        'vencimento_carga': _date_iso(equipamento.vencimento_carga),
        'vencimento_teste_hidrostatico': _date_iso(equipamento.vencimento_teste_hidrostatico),
        'is_extintor': equipamento.is_extintor(),
        'foto_url': _absolute_media_url(request, equipamento.foto),
        'qr_code_url': _absolute_media_url(request, equipamento.qr_code),
        'ativo': equipamento.ativo,
    }


def _tipo_servico_api_data(config):
    return {
        'id': config.tipo_servico_id,
        'nome': config.tipo_servico.nome if config.tipo_servico else 'Serviço',
        'descricao': config.tipo_servico.descricao if config.tipo_servico else '',
        'periodicidade_nome': config.periodicidade.get_rotulo_inspecao() if config.periodicidade else '-',
        'obrigatorio': config.obrigatorio,
        'habilitar_assinatura': config.habilitar_assinatura,
        'assinatura_obrigatoria': config.assinatura_obrigatoria,
        'acoes_obrigatorias': config.acoes_obrigatorias,
    }


def _usuario_nome_simples(user):
    if not user:
        return ''
    return user.get_full_name() or user.username


def _tipos_servico_equipamento(equipamento):
    if not equipamento.tipo_equipamento_id:
        return []

    configs = (
        ServicoTipoEquipamento.objects
        .filter(tipo_equipamento=equipamento.tipo_equipamento, ativo=True, tipo_servico__ativo=True)
        .select_related('tipo_servico', 'periodicidade')
        .order_by('tipo_servico__nome')
    )
    return [_tipo_servico_api_data(config) for config in configs]


def _extract_equipamento_id_from_qr(raw_value):
    value = str(raw_value or '').strip()
    if not value:
        return None

    if value.isdigit():
        return int(value)

    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    for key in ['equipamento_id', 'equipamento', 'id']:
        candidate = query.get(key, [''])[0]
        if str(candidate).isdigit():
            return int(candidate)

    match = re.search(r'/equipamentos/(\d+)/?', parsed.path or value)
    if match:
        return int(match.group(1))

    match = re.search(r'(?:equipamento|equipamentos|eq)[^0-9]*(\d+)', value, re.IGNORECASE)
    if match:
        return int(match.group(1))

    numbers = re.findall(r'\d+', value)
    if len(numbers) == 1:
        return int(numbers[0])

    return None


class IsGestorForWrites(BasePermission):
    message = 'Você não tem permissão para criar, atualizar ou excluir informações do sistema.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class LoginAPI(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        empresa = resolve_empresa_ativa(request, user=token.user)
        if getattr(request, 'empresa_acesso_negado', False):
            return Response(
                {'detail': 'Usuário sem acesso a esta empresa.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response({
            'token': token.key,
            'user_id': token.user_id,
            'username': token.user.username,
            'usuario': _usuario_api_data(request, token.user),
            'empresa': _empresa_api_data(empresa),
        })


class PerfilAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({
            'success': True,
            'usuario': _usuario_api_data(request, request.user),
            'empresa': _empresa_api_data(getattr(request, 'empresa_ativa', None)),
        })


def _notificacao_api_data(notificacao):
    resposta = notificacao.resposta_checklist
    item = resposta.item_checklist if resposta else None
    equipamento = notificacao.equipamento

    return {
        'id': notificacao.id,
        'tipo': notificacao.tipo,
        'titulo': notificacao.titulo,
        'mensagem': notificacao.mensagem,
        'lida': notificacao.lida,
        'criado_em': timezone.localtime(notificacao.criado_em).strftime('%d/%m/%Y %H:%M'),
        'equipamento_nome': equipamento.nome if equipamento else '',
        'item_pergunta': item.pergunta if item else '',
        'observacao': resposta.observacao if resposta and resposta.observacao else '',
        'servico_id': notificacao.servico_id,
    }


class NotificacoesAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        notificacoes = (
            Notificacao.objects
            .filter(destinatario=request.user)
            .select_related('equipamento', 'servico', 'resposta_checklist__item_checklist')
            .order_by('-criado_em')[:20]
        )
        notificacoes_data = [_notificacao_api_data(notificacao) for notificacao in notificacoes]

        return Response({
            'success': True,
            'nao_lidas': sum(1 for notificacao in notificacoes_data if not notificacao['lida']),
            'notificacoes': notificacoes_data,
        })


def _datetime_br(value):
    return timezone.localtime(value).strftime('%d/%m/%Y %H:%M') if value else ''


def _alerta_checklist_api_data(alerta):
    resposta = alerta.resposta_checklist
    item = resposta.item_checklist if resposta else None
    equipamento = alerta.equipamento
    servico = alerta.servico

    return {
        'id': alerta.id,
        'status': alerta.status,
        'status_label': alerta.get_status_display(),
        'resolvido': alerta.status == 'resolvido',
        'equipamento_id': equipamento.id if equipamento else None,
        'equipamento_nome': equipamento.nome if equipamento else '',
        'equipamento_codigo': (
            equipamento.numero_serie
            or equipamento.numero_extintor
            or equipamento.numero_cilindro
            or ''
        ) if equipamento else '',
        'servico_id': alerta.servico_id,
        'tipo_servico_nome': servico.tipo_servico.nome if servico and servico.tipo_servico else '',
        'item_pergunta': item.pergunta if item else '',
        'observacao': resposta.observacao if resposta and resposta.observacao else '',
        'criado_em': _datetime_br(alerta.criado_em),
        'checklist_enviado_em': _datetime_br(servico.criado_em if servico else alerta.criado_em),
        'tratativa': alerta.tratativa or '',
        'resolvido_por_nome': _usuario_nome_simples(alerta.resolvido_por),
        'resolvido_em': _datetime_br(alerta.resolvido_em),
    }


class AlertasChecklistMobileAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        alertas = (
            AlertaChecklist.objects
            .filter(criado_por=request.user)
            .select_related(
                'equipamento',
                'servico',
                'servico__tipo_servico',
                'resposta_checklist',
                'resposta_checklist__item_checklist',
                'resolvido_por',
            )
            .order_by('-criado_em')
        )

        alertas_data = [_alerta_checklist_api_data(alerta) for alerta in alertas]

        return Response({
            'success': True,
            'pendentes': sum(1 for alerta in alertas_data if alerta['status'] == 'pendente'),
            'resolvidos': sum(1 for alerta in alertas_data if alerta['status'] == 'resolvido'),
            'alertas': alertas_data,
        })


class QRCodeEquipamentoAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        raw_value = request.query_params.get('valor') or request.query_params.get('value') or request.query_params.get('qr') or request.query_params.get('equipamento_id') or request.query_params.get('id')
        equipamento_id = _extract_equipamento_id_from_qr(raw_value)
        if not equipamento_id:
            return Response({'success': False, 'error': 'QR Code não identificado como equipamento.'}, status=400)

        equipamento = get_object_or_404(
            Equipamento.objects.select_related('tipo_equipamento', 'grupo', 'predio'),
            id=equipamento_id,
            ativo=True,
        )

        return Response({
            'success': True,
            'equipamento': _equipamento_api_data(request, equipamento),
            'tipos_servico': _tipos_servico_equipamento(equipamento),
        })


def _departamento_api_data(departamento):
    return {
        'id': departamento.id,
        'nome': departamento.nome,
        'descricao': departamento.descricao or '',
        'localizacao': departamento.localizacao or '',
        'responsavel': departamento.responsavel or '',
        'email': departamento.email or '',
        'telefone': departamento.telefone or '',
        'ativo': departamento.ativo,
        'equipamentos_count': getattr(departamento, 'equipamentos_count', 0),
    }


def _predio_api_data(predio):
    departamentos = [
        _departamento_api_data(departamento)
        for departamento in predio.departamentos.all()
    ]
    return {
        'id': predio.id,
        'nome': predio.nome,
        'descricao': predio.descricao or '',
        'endereco': predio.endereco or '',
        'ativo': predio.ativo,
        'departamentos_count': len(departamentos),
        'equipamentos_count': getattr(predio, 'equipamentos_count', 0),
        'departamentos': departamentos,
    }


class PrediosAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        predios = (
            Predio.objects
            .annotate(equipamentos_count=Count('equipamentos', distinct=True))
            .prefetch_related(
                'departamentos',
                'departamentos__equipamentos',
            )
            .order_by('nome')
        )

        for predio in predios:
            departamentos = list(predio.departamentos.all())
            for departamento in departamentos:
                departamento.equipamentos_count = departamento.equipamentos.count()

        return Response({
            'success': True,
            'predios': [_predio_api_data(predio) for predio in predios],
        })


class EquipamentoTiposServicoAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        equipamento = get_object_or_404(Equipamento.objects.select_related('tipo_equipamento'), id=id, ativo=True)
        return Response({'success': True, 'data': _tipos_servico_equipamento(equipamento)})


class ChecklistItensAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tipo_equipamento_id = request.query_params.get('tipo_equipamento_id')
        tipo_servico_id = request.query_params.get('tipo_servico_id')

        if not tipo_equipamento_id or not tipo_servico_id:
            return Response({'success': False, 'error': 'Informe equipamento e tipo de serviço.'}, status=400)

        tipo_equipamento = get_object_or_404(TipoEquipamento, id=tipo_equipamento_id)
        tipo_servico = get_object_or_404(TipoServico, id=tipo_servico_id)
        configs = (
            ServicoTipoEquipamento.objects
            .filter(tipo_equipamento=tipo_equipamento, tipo_servico=tipo_servico, ativo=True)
            .select_related('tipo_servico', 'periodicidade')
            .prefetch_related('secoes_checklist__itens')
        )

        itens = []
        for config in configs:
            for secao in config.secoes_checklist.filter(ativo=True).order_by('ordem', 'nome'):
                for item in secao.itens.filter(ativo=True).order_by('ordem', 'id'):
                    itens.append({
                        'id': item.id,
                        'pergunta': item.pergunta,
                        'tipo_resposta': item.tipo_resposta,
                        'obrigatorio': item.obrigatorio,
                        'ordem': item.ordem,
                        'secao_nome': secao.nome,
                        'servico_nome': config.tipo_servico.nome if config.tipo_servico else '-',
                        'periodicidade_nome': config.periodicidade.get_rotulo_inspecao() if config.periodicidade else '-',
                    })

        return Response({
            'success': True,
            'data': itens,
            'itens': itens,
            'tipo_servico_nome': tipo_servico.nome,
        })


class ServicoCriarAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated, IsGestorForWrites]

    def get_permissions(self):
        if self.request.path.startswith('/api/mobile/'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def post(self, request, *args, **kwargs):
        equipamento_id = request.data.get('equipamento_id')
        tipo_servico_id = request.data.get('tipo_servico_id')
        respostas_raw = request.data.get('respostas') or []
        observacoes = request.data.get('observacoes') or ''
        status = request.data.get('status') or 'concluido'

        if status not in ['rascunho', 'concluido']:
            return Response({'success': False, 'error': 'Status inválido.'}, status=400)

        if isinstance(respostas_raw, str):
            try:
                respostas = json.loads(respostas_raw or '[]')
            except json.JSONDecodeError:
                return Response({'success': False, 'error': 'Respostas do checklist inválidas.'}, status=400)
        else:
            respostas = respostas_raw

        if not isinstance(respostas, list):
            return Response({'success': False, 'error': 'Respostas do checklist inválidas.'}, status=400)

        equipamento = get_object_or_404(Equipamento, id=equipamento_id, ativo=True)
        tipo_servico = get_object_or_404(TipoServico, id=tipo_servico_id)

        if not ServicoTipoEquipamento.objects.filter(
            tipo_equipamento=equipamento.tipo_equipamento,
            tipo_servico=tipo_servico,
            ativo=True,
        ).exists():
            return Response({'success': False, 'error': 'Serviço não configurado para este equipamento.'}, status=400)

        servico = Servico.objects.create(
            equipamento=equipamento,
            tipo_servico=tipo_servico,
            observacoes=observacoes,
            status=status,
            realizado_por=request.user,
        )

        pontuacao_total = 0
        pontuacao_maxima = 0
        respostas_nao_atendem = []
        for resposta in respostas:
            if not isinstance(resposta, dict):
                continue

            item_id = resposta.get('item_id')
            opcao = resposta.get('opcao')
            observacao = resposta.get('observacao') or ''
            foto_field = resposta.get('foto_field') or ''
            if opcao not in ['atende', 'nao_atende', 'nao_aplica']:
                continue

            item = get_object_or_404(ItemChecklist, id=item_id, ativo=True)
            resposta_salva = RespostaChecklist.objects.create(
                servico=servico,
                item_checklist=item,
                opcao=opcao,
                observacao=observacao,
                fotos=request.FILES.get(foto_field) if foto_field else None,
            )
            if status == 'concluido' and opcao == 'nao_atende':
                respostas_nao_atendem.append(resposta_salva)

            if opcao != 'nao_aplica':
                pontuacao_maxima += 1
                if opcao == 'atende':
                    pontuacao_total += 1

        servico.pontuacao_total = pontuacao_total
        servico.pontuacao_maxima = pontuacao_maxima
        servico.save(update_fields=['pontuacao_total', 'pontuacao_maxima', 'atualizado_em'])

        for resposta in respostas_nao_atendem:
            notificar_checklist_nao_atende(servico, resposta)

        return Response({
            'success': True,
            'message': 'Checklist concluído com sucesso!' if status == 'concluido' else 'Rascunho salvo com sucesso!',
            'servico_id': servico.id,
            'pontuacao_percentual': float(servico.calcular_pontuacao_percentual()),
        })


class ServicoDetalheAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        servico = get_object_or_404(
            Servico.objects.select_related(
                'equipamento',
                'equipamento__predio',
                'equipamento__departamento',
                'equipamento__grupo',
                'equipamento__tipo_equipamento',
                'tipo_servico',
                'realizado_por',
            ).prefetch_related('respostas__item_checklist__secao'),
            id=id,
            status='concluido',
        )

        respostas = []
        respostas_queryset = (
            servico.respostas
            .select_related('item_checklist', 'item_checklist__secao')
            .order_by('item_checklist__secao__ordem', 'item_checklist__ordem', 'id')
        )
        for resposta in respostas_queryset:
            item = resposta.item_checklist
            foto_url = _absolute_media_url(request, resposta.fotos)
            respostas.append({
                'id': resposta.id,
                'item_id': resposta.item_checklist_id,
                'pergunta': item.pergunta,
                'secao_nome': item.secao.nome if item.secao else 'Checklist',
                'opcao': resposta.opcao,
                'opcao_display': resposta.get_opcao_display() if resposta.opcao else '-',
                'observacao': resposta.observacao or '',
                'foto': foto_url,
                'foto_url': foto_url,
                'fotos_url': foto_url,
            })

        total_itens = len(respostas)
        itens_atende = sum(1 for resposta in respostas if resposta['opcao'] == 'atende')
        itens_nao_atende = sum(1 for resposta in respostas if resposta['opcao'] == 'nao_atende')
        itens_nao_aplica = sum(1 for resposta in respostas if resposta['opcao'] == 'nao_aplica')

        equipamento = servico.equipamento
        data_realizacao = timezone.localtime(servico.criado_em)

        return Response({
            'success': True,
            'data': {
                'id': servico.id,
                'status': servico.status,
                'equipamento': _equipamento_api_data(request, equipamento),
                'equipamento_id': equipamento.id,
                'equipamento_nome': equipamento.nome,
                'equipamento_numero_serie': equipamento.numero_serie or equipamento.numero_extintor or '',
                'tipo_servico_id': servico.tipo_servico_id,
                'tipo_servico_nome': servico.tipo_servico.nome if servico.tipo_servico else '-',
                'data_realizacao': data_realizacao.strftime('%d/%m/%Y %H:%M'),
                'data_realizacao_iso': data_realizacao.isoformat(),
                'realizado_por_nome': _usuario_nome_simples(servico.realizado_por),
                'observacoes': servico.observacoes or '',
                'total_itens': total_itens,
                'itens_atende': itens_atende,
                'itens_nao_atende': itens_nao_atende,
                'itens_nao_aplica': itens_nao_aplica,
                'pontuacao_percentual': float(servico.calcular_pontuacao_percentual()),
                'respostas': respostas,
            },
        })


class EquipamentoViewSet(EmpresaAtivaAPIMixin, viewsets.ModelViewSet):
    serializer_class = EquipamentoSerializer
    permission_classes = [IsAuthenticated, IsGestorForWrites]

    def get_queryset(self):
        return _equipamentos_queryset_from_request(self.request)


def _equipamentos_queryset_from_request(request):
    queryset = (
        Equipamento.objects
        .select_related('tipo_equipamento', 'grupo', 'predio', 'departamento')
        .all()
        .order_by('-id')
    )

    predio_id = request.query_params.get('predio_id')
    departamento_id = request.query_params.get('departamento_id')
    grupo_id = request.query_params.get('grupo_id')
    status_param = (request.query_params.get('status') or '').strip().lower()
    search = (request.query_params.get('q') or request.query_params.get('search') or '').strip()

    if predio_id:
        queryset = queryset.filter(predio_id=predio_id)
    if departamento_id:
        queryset = queryset.filter(departamento_id=departamento_id)
    if grupo_id:
        queryset = queryset.filter(grupo_id=grupo_id)
    if status_param in ['ativo', 'ativos', 'true', '1']:
        queryset = queryset.filter(ativo=True)
    elif status_param in ['inativo', 'inativos', 'false', '0']:
        queryset = queryset.filter(ativo=False)
    if search:
        queryset = queryset.filter(
            Q(nome__icontains=search)
            | Q(numero_serie__icontains=search)
            | Q(numero_extintor__icontains=search)
            | Q(numero_cilindro__icontains=search)
            | Q(marca__icontains=search)
            | Q(local__icontains=search)
            | Q(ponto_referencia__icontains=search)
            | Q(descricao__icontains=search)
            | Q(observacoes__icontains=search)
            | Q(tipo_equipamento__nome__icontains=search)
            | Q(grupo__nome__icontains=search)
            | Q(predio__nome__icontains=search)
            | Q(departamento__nome__icontains=search)
        )

    return queryset


class EquipamentosMobileAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = EquipamentoSerializer(
            _equipamentos_queryset_from_request(request),
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)


class EquipamentoDetalheMobileAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        equipamento = get_object_or_404(
            Equipamento.objects.select_related('tipo_equipamento', 'grupo', 'predio', 'departamento'),
            id=id,
        )
        serializer = EquipamentoSerializer(equipamento, context={'request': request})
        return Response(serializer.data)


class DashboardAPI(EmpresaAtivaAPIMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        hoje = timezone.localdate()
        params = {
            'ano': request.query_params.get('ano') or hoje.year,
            'mes': request.query_params.get('mes') or hoje.month,
        }

        dados_calendario = _calendario_eventos_data(params)
        eventos = dados_calendario.get('eventos', [])
        hoje_iso = hoje.strftime('%Y-%m-%d')

        eventos_realizados = [
            evento for evento in eventos
            if evento.get('status') == 'realizada'
        ]
        eventos_para_inspecionar = [
            evento for evento in eventos
            if evento.get('status') in ['pendente', 'vencida']
        ]
        tarefas_hoje = [
            evento for evento in eventos_para_inspecionar
            if evento.get('status') == 'vencida' or evento.get('data_original') == hoje_iso
        ]

        inicio_mes = dados_calendario.get('inicio')
        fim_mes = dados_calendario.get('fim')
        servicos_mes = Servico.objects.filter(status='concluido')
        if inicio_mes and fim_mes:
            servicos_mes = servicos_mes.filter(criado_em__date__gte=inicio_mes, criado_em__date__lte=fim_mes)

        equipamentos_total = Equipamento.objects.count()
        equipamentos_ativos = Equipamento.objects.filter(ativo=True).count()
        equipamentos_inspecionados_mes = servicos_mes.values('equipamento_id').distinct().count()
        equipamentos_para_inspecionar = len({
            evento.get('equipamento_id')
            for evento in eventos_para_inspecionar
            if evento.get('equipamento_id')
        })

        return Response({
            'success': True,
            'periodo': {
                'ano': dados_calendario.get('ano'),
                'mes': dados_calendario.get('mes'),
                'inicio': inicio_mes,
                'fim': fim_mes,
                'hoje': hoje_iso,
            },
            'equipamentos': {
                'total': equipamentos_total,
                'ativos': equipamentos_ativos,
                'inativos': max(equipamentos_total - equipamentos_ativos, 0),
                'inspecionados_mes': equipamentos_inspecionados_mes,
                'para_inspecionar': equipamentos_para_inspecionar,
            },
            'servicos': {
                'concluidos_hoje': sum(1 for evento in eventos_realizados if evento.get('data_calendario') == hoje_iso),
                'concluidos_mes': len(eventos_realizados),
                'pendentes': dados_calendario.get('resumo', {}).get('pendentes', 0),
                'vencidos': dados_calendario.get('resumo', {}).get('vencidas', 0),
            },
            'acoes': {
                'pendentes': AcaoCorretiva.objects.count(),
            },
            'eventos_calendario': eventos,
            'tarefas_hoje': tarefas_hoje[:20],
            'tarefas_para_inspecionar': eventos_para_inspecionar[:50],
            'ultimas_inspecoes': eventos_realizados[-10:],
        })

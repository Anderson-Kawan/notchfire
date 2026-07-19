from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from .models import AlertaChecklist, Notificacao


PERFIS_RESPONSAVEIS_CHECKLIST = ['admin', 'supervisor', 'analista']


def _usuario_nome_simples(user):
    if not user:
        return ''
    return user.get_full_name() or user.username


def _usuarios_responsaveis_notificacao(empresa):
    usuarios = User.objects.filter(is_active=True)

    if empresa:
        return (
            usuarios
            .filter(empresas__empresa=empresa, empresas__ativo=True)
            .filter(
                Q(empresas__tipo_acesso__in=PERFIS_RESPONSAVEIS_CHECKLIST)
                | Q(perfil__tipo_acesso__in=PERFIS_RESPONSAVEIS_CHECKLIST, perfil__status='ativo')
            )
            .distinct()
        )

    return (
        usuarios
        .filter(perfil__tipo_acesso__in=PERFIS_RESPONSAVEIS_CHECKLIST, perfil__status='ativo')
        .distinct()
    )


def notificar_checklist_nao_atende(servico, resposta):
    empresa = servico.empresa or servico.equipamento.empresa
    equipamento = servico.equipamento
    item = resposta.item_checklist
    AlertaChecklist.objects.get_or_create(
        resposta_checklist=resposta,
        defaults={
            'empresa': empresa,
            'equipamento': equipamento,
            'servico': servico,
            'criado_por': servico.realizado_por,
            'status': 'pendente',
        },
    )
    data_registro = timezone.localtime(resposta.criado_em).strftime('%d/%m/%Y %H:%M')
    realizado_por = _usuario_nome_simples(servico.realizado_por) or 'Usuário não identificado'
    observacao = (resposta.observacao or '').strip()

    linhas = [
        'Existe um item do checklist marcado como "Não atende".',
        f'Equipamento: {equipamento.nome}',
        f'Item do checklist: {item.pergunta}',
        f'Data e horário: {data_registro}',
        f'Usuário: {realizado_por}',
    ]
    if observacao:
        linhas.append(f'Observação: {observacao}')

    destinatarios = (
        _usuarios_responsaveis_notificacao(empresa)
        .exclude(
            notificacoes__tipo='checklist_nao_atende',
            notificacoes__resposta_checklist=resposta,
        )
        .distinct()
    )
    notificacoes = [
        Notificacao(
            empresa=empresa,
            destinatario=destinatario,
            criado_por=servico.realizado_por,
            tipo='checklist_nao_atende',
            titulo='Item de checklist não atende',
            mensagem='\n'.join(linhas),
            equipamento=equipamento,
            servico=servico,
            resposta_checklist=resposta,
        )
        for destinatario in destinatarios
    ]
    if notificacoes:
        Notificacao.objects.bulk_create(notificacoes)

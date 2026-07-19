from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import redirect
from . import views


def _pode_gerenciar(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


def gestor_required(view_func):
    def wrapper(request, *args, **kwargs):
        if _pode_gerenciar(request.user):
            return view_func(request, *args, **kwargs)

        if request.path.startswith('/api/') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para criar, atualizar ou excluir informações do sistema.'
            }, status=403)

        return redirect('home')

    return wrapper


urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),

    # Usuários
    path('usuarios/', gestor_required(views.usuarios_view), name='usuarios'),
    path('criar_usuario/', gestor_required(views.criar_usuario_view), name='criar_usuario'),
    path('minha_conta/', views.minha_conta_view, name='minha_conta'),
    path('api/usuarios/', gestor_required(views.api_usuarios_listar), name='api_usuarios_listar'),
    path('api/usuarios/criar/', gestor_required(views.api_usuarios_criar), name='api_usuarios_criar'),
    path('api/usuarios/<int:id>/', gestor_required(views.api_usuarios_detalhe), name='api_usuarios_detalhe'),

    # Equipamentos
    path('equipamentos/', views.equipamentos_view, name='equipamentos'),
    path('equipamentos/criar/', gestor_required(views.criar_equipamento_view), name='criar_equipamento'),
    path('equipamentos/<int:id>/', views.detalhe_equipamento_view, name='detalhe_equipamento'),
    path('equipamentos/<int:id>/editar/', gestor_required(views.editar_equipamento_view), name='editar_equipamento'),

    # API Equipamentos
    path('api/equipamentos/', views.api_equipamentos_listar, name='api_equipamentos_listar'),
    path('api/equipamentos-para-servico/', views.api_equipamentos_para_servico, name='api_equipamentos_para_servico'),
    path('api/equipamentos/<int:id>/', views.api_equipamento_detalhes, name='api_equipamento_detalhes'),
    path('api/equipamentos/<int:id>/editar/', gestor_required(views.api_equipamento_editar_detalhe), name='api_equipamento_editar_detalhe'),
    path('api/equipamentos/<int:id>/toggle-ativo/', gestor_required(views.api_equipamento_toggle_ativo), name='api_equipamento_toggle_ativo'),
    path('api/equipamentos/<int:id>/foto/', gestor_required(views.api_equipamento_upload_foto), name='api_equipamento_upload_foto'),
    path('api/equipamentos/<int:id>/excluir/', gestor_required(views.api_equipamento_excluir), name='api_equipamento_excluir'),

    # Departamentos
    path('departamentos/', gestor_required(views.departamentos_view), name='departamentos'),

    # API Departamentos
    path('api/departamentos/', gestor_required(views.api_departamentos_listar), name='api_departamentos_listar'),
    path('api/departamentos/criar/', gestor_required(views.api_departamentos_criar), name='api_departamentos_criar'),
    path('api/departamentos/<int:departamento_id>/equipamentos/', views.api_departamento_equipamentos, name='api_departamento_equipamentos'),
    path('api/departamentos/<int:id>/editar/', gestor_required(views.api_departamentos_editar), name='api_departamentos_editar'),
    path('api/departamentos/<int:id>/excluir/', gestor_required(views.api_departamentos_excluir), name='api_departamentos_excluir'),
    path('api/departamentos-por-predio/', gestor_required(views.api_departamentos_por_predio), name='api_departamentos_por_predio'),
    path('api/departamentos-para-select/', gestor_required(views.api_departamentos_para_select), name='api_departamentos_para_select'),
    path('api/navegacao/predios/', views.api_navegacao_predios, name='api_navegacao_predios'),
    path('api/navegacao/departamentos/', views.api_navegacao_departamentos, name='api_navegacao_departamentos'),
    path('api/navegacao/predios/<int:predio_id>/departamentos/', views.api_navegacao_departamentos, name='api_navegacao_departamentos_por_predio'),
    path('api/navegacao/equipamentos/', views.api_navegacao_equipamentos, name='api_navegacao_equipamentos'),
    path(
        'api/navegacao/predios/<int:predio_id>/departamentos/<int:departamento_id>/equipamentos/',
        views.api_navegacao_equipamentos,
        name='api_navegacao_equipamentos_por_departamento',
    ),
    path('api/navegacao/equipamentos/<int:id>/', views.api_navegacao_equipamento_detalhe, name='api_navegacao_equipamento_detalhe'),

    # Grupos
    path('grupos/', gestor_required(views.grupos_view), name='grupos'),

    # API Grupos
    path('api/grupos/', gestor_required(views.api_grupos_listar), name='api_grupos_listar'),
    path('api/grupos/criar/', gestor_required(views.api_grupos_criar), name='api_grupos_criar'),
    path('api/grupos/<int:id>/editar/', gestor_required(views.api_grupos_editar), name='api_grupos_editar'),
    path('api/grupos/<int:id>/excluir/', gestor_required(views.api_grupos_excluir), name='api_grupos_excluir'),
    path('api/grupos-para-select/', gestor_required(views.api_grupos_listar_para_select), name='api_grupos_para_select'),

    # Tipos de Serviço
    path('tipos-servico/', gestor_required(views.tipos_servico_view), name='tipos_servico'),

    # API Tipos de Serviço
    path('api/tipos-servico/', gestor_required(views.api_tipos_servico_listar), name='api_tipos_servico_listar'),
    path('api/tipos-servico/criar/', gestor_required(views.api_tipos_servico_criar), name='api_tipos_servico_criar'),
    path('api/tipos-servico/<int:id>/editar/', gestor_required(views.api_tipos_servico_editar), name='api_tipos_servico_editar'),
    path('api/tipos-servico/<int:id>/excluir/', gestor_required(views.api_tipos_servico_excluir), name='api_tipos_servico_excluir'),

    # Periodicidades
    path('periodicidades/', gestor_required(views.periodicidades_view), name='periodicidades'),

    # API Periodicidades
    path('api/periodicidades/', gestor_required(views.api_periodicidades_listar), name='api_periodicidades_listar'),
    path('api/periodicidades/criar/', gestor_required(views.api_periodicidades_criar), name='api_periodicidades_criar'),
    path('api/periodicidades/<int:id>/editar/', gestor_required(views.api_periodicidades_editar), name='api_periodicidades_editar'),
    path('api/periodicidades/<int:id>/excluir/', gestor_required(views.api_periodicidades_excluir), name='api_periodicidades_excluir'),
    path('api/periodicidades-para-select/', gestor_required(views.api_periodicidades_para_select), name='api_periodicidades_para_select'),

    # Tipos de Equipamento
    path('tipos-equipamento/', gestor_required(views.tipos_equipamento_view), name='tipos_equipamento'),
    path('tipos-equipamento/<int:id>/', gestor_required(views.detalhe_tipo_equipamento_view), name='detalhe_tipo_equipamento'),

    # API Tipos de Equipamento
    path('api/tipos-equipamento/', gestor_required(views.api_tipos_equipamento_listar), name='api_tipos_equipamento_listar'),
    path('api/tipos-equipamento/criar/', gestor_required(views.api_tipos_equipamento_criar), name='api_tipos_equipamento_criar'),
    path('api/tipos-equipamento/<int:id>/editar/', gestor_required(views.api_tipos_equipamento_editar), name='api_tipos_equipamento_editar'),
    path('api/tipos-equipamento/<int:id>/excluir/', gestor_required(views.api_tipos_equipamento_excluir), name='api_tipos_equipamento_excluir'),
    path('api/tipos-equipamento/<int:id>/info/', gestor_required(views.api_tipo_equipamento_info), name='api_tipo_equipamento_info'),
    path('api/tipo-equipamento-detalhe/', gestor_required(views.api_tipo_equipamento_detalhe), name='api_tipo_equipamento_detalhe'),
    path('api/tipos-equipamento/servicos/criar/', gestor_required(views.api_editor_servico_criar), name='api_editor_servico_criar'),
    path('api/tipos-equipamento/servicos/<int:id>/', views.api_editor_servico_detalhes, name='api_editor_servico_detalhes'),
    path('api/tipos-equipamento/servicos/<int:id>/editar/', gestor_required(views.api_editor_servico_editar), name='api_editor_servico_editar'),
    path('api/tipos-equipamento/servicos/<int:id>/excluir/', gestor_required(views.api_editor_servico_excluir), name='api_editor_servico_excluir'),
    path('api/tipos-equipamento/servicos/<int:id>/checklist/apagar/', gestor_required(views.api_editor_checklist_apagar), name='api_editor_checklist_apagar'),
    path('api/secoes-checklist/criar/', gestor_required(views.api_editor_secao_criar), name='api_editor_secao_criar'),
    path('api/secoes-checklist/<int:id>/editar/', gestor_required(views.api_editor_secao_editar), name='api_editor_secao_editar'),
    path('api/secoes-checklist/<int:id>/excluir/', gestor_required(views.api_editor_secao_excluir), name='api_editor_secao_excluir'),
    path('api/itens-checklist/criar/', gestor_required(views.api_editor_item_criar), name='api_editor_item_criar'),
    path('api/itens-checklist/<int:id>/editar/', gestor_required(views.api_editor_item_editar), name='api_editor_item_editar'),
    path('api/itens-checklist/<int:id>/excluir/', gestor_required(views.api_editor_item_excluir), name='api_editor_item_excluir'),
    path('api/checklist-itens/criar/', gestor_required(views.api_checklist_item_criar), name='api_checklist_item_criar'),
    path('api/checklist-itens/<int:id>/', gestor_required(views.api_checklist_item_detalhes), name='api_checklist_item_detalhes'),
    path('api/checklist-itens/<int:id>/editar/', gestor_required(views.api_checklist_item_editar), name='api_checklist_item_editar'),
    path('api/checklist-itens/<int:id>/excluir/', gestor_required(views.api_checklist_item_excluir), name='api_checklist_item_excluir'),

    # Serviços do Tipo de Equipamento
    path('tipos-equipamento/<int:tipo_id>/servicos/criar/', gestor_required(views.criar_servico_tipo_equipamento_view), name='criar_servico_tipo_equipamento'),
    path('servicos-tipo-equipamento/<int:id>/editar/', gestor_required(views.editar_servico_tipo_equipamento_view), name='editar_servico_tipo_equipamento'),
    path('servicos-tipo-equipamento/<int:id>/excluir/', gestor_required(views.excluir_servico_tipo_equipamento_view), name='excluir_servico_tipo_equipamento'),

    # Seções do Checklist
    path('servicos-tipo-equipamento/<int:servico_id>/secoes/criar/', gestor_required(views.criar_secao_checklist_view), name='criar_secao_checklist'),
    path('secoes-checklist/<int:id>/editar/', gestor_required(views.editar_secao_checklist_view), name='editar_secao_checklist'),
    path('secoes-checklist/<int:id>/excluir/', gestor_required(views.excluir_secao_checklist_view), name='excluir_secao_checklist'),

    # Itens do Checklist
    path('servicos-tipo-equipamento/<int:servico_id>/itens/criar/', gestor_required(views.criar_item_checklist_view), name='criar_item_checklist'),
    path('itens-checklist/<int:id>/editar/', gestor_required(views.editar_item_checklist_view), name='editar_item_checklist'),
    path('itens-checklist/<int:id>/excluir/', gestor_required(views.excluir_item_checklist_view), name='excluir_item_checklist'),

    # Prédios
    path('predios/', views.predios_view, name='predios'),

    # API Prédios
    path('api/predios/', views.api_predios_listar, name='api_predios_listar'),
    path('api/predios/criar/', gestor_required(views.api_predios_criar), name='api_predios_criar'),
    path('api/predios/<int:predio_id>/departamentos/', views.api_predio_departamentos, name='api_predio_departamentos'),
    path('api/predios/<int:id>/editar/', gestor_required(views.api_predios_editar), name='api_predios_editar'),
    path('api/predios/<int:id>/excluir/', gestor_required(views.api_predios_excluir), name='api_predios_excluir'),
    path('api/predios-para-select/', views.api_predios_para_select, name='api_predios_para_select'),

    # Serviços realizados
    path('servicos/', views.servicos_view, name='servicos'),
    path('calendario/', views.calendario_view, name='calendario'),
    path('relatorios/', gestor_required(views.relatorios_view), name='relatorios'),
    path('rascunho/', views.rascunhos_view, name='rascunho'),
    path('rascunhos/', views.rascunhos_view, name='rascunhos'),
    path('api/calendario/filtros/', views.api_calendario_filtros, name='api_calendario_filtros'),
    path('api/calendario/eventos/', views.api_calendario_eventos, name='api_calendario_eventos'),
    path('calendario/exportar/', gestor_required(views.exportar_calendario_dados), name='exportar_calendario_dados'),
    path('api/servicos/', views.api_servicos_listar, name='api_servicos_listar'),
    path('api/servicos/criar/', gestor_required(views.api_servicos_criar), name='api_servicos_criar'),
    path('api/servicos/<int:id>/', views.api_servicos_detalhes, name='api_servicos_detalhes'),
    path('api/servicos/<int:id>/atualizar/', gestor_required(views.api_servicos_atualizar), name='api_servicos_atualizar'),
    path('api/servicos/rascunho/', views.api_servicos_rascunho, name='api_servicos_rascunho'),
    path('api/servicos/<int:id>/descartar/', gestor_required(views.api_servicos_descartar), name='api_servicos_descartar'),
    path('api/rascunhos/', views.api_rascunhos_listar, name='api_rascunhos_listar'),
    path('api/relatorios/filtros/', views.api_relatorios_filtros, name='api_relatorios_filtros'),
    path('api/relatorios/resumo/', views.api_relatorios_resumo, name='api_relatorios_resumo'),
    path('api/relatorios/historico/', views.api_relatorios_historico, name='api_relatorios_historico'),
    path('relatorios/exportar/condensado/', gestor_required(views.exportar_relatorio_condensado), name='exportar_relatorio_condensado'),
    path('relatorios/<int:id>/baixar/', views.baixar_relatorio_gerado, name='baixar_relatorio_gerado'),
    path('api/tipos-servico-para-equipamento/', gestor_required(views.api_tipos_servico_para_equipamento), name='api_tipos_servico_para_equipamento'),
    path('api/checklist-itens-por-tipo/', gestor_required(views.api_checklist_itens_por_tipo), name='api_checklist_itens_por_tipo'),
    path('api/acoes-corretivas/criar/', gestor_required(views.api_acoes_corretivas_criar), name='api_acoes_corretivas_criar'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.utils import timezone
from .models import (
    AlertaChecklist,
    Departamento,
    Empresa,
    EmpresaUsuario,
    Equipamento,
    Grupo,
    Notificacao,
    Periodicidade,
    Predio,
    TipoEquipamento,
    TipoServico,
    UsuarioPerfil,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'slug', 'documento', 'dominio', 'ativa', 'criado_em')
    list_filter = ('ativa', 'criado_em')
    search_fields = ('nome', 'slug', 'documento', 'dominio')
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(EmpresaUsuario)
class EmpresaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'user', 'tipo_acesso', 'ativo', 'criado_em')
    list_filter = ('empresa', 'tipo_acesso', 'ativo')
    search_fields = ('empresa__nome', 'user__username', 'user__email', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('empresa', 'user')


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'empresa',
        'numero_serie',
        'marca',
        'tipo_equipamento',
        'empresa',
        'grupo',
        'predio',
        'departamento',
        'local',
        'possui_vencimento',
        'criado_em',
        'ativo',
    )

    search_fields = (
        'nome',
        'numero_serie',
        'marca',
        'tipo_equipamento__nome',
        'grupo__nome',
        'predio__nome',
        'departamento__nome',
        'local',
        'ponto_referencia',
        'descricao',
    )

    list_filter = (
        'tipo_equipamento',
        'grupo',
        'predio',
        'departamento',
        'ativo',
        'criado_em',
    )
    
    readonly_fields = ('qr_code', 'criado_em', 'atualizado_em')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'nome', 'numero_serie', 'marca', 'data_fabricacao')
        }),
        ('Especificações', {
            'fields': ('tipo_equipamento', 'grupo')
        }),
        ('Vencimentos', {
            'fields': (
                'possui_vencimento',
                'data_vencimento',
                'vencimento_carga',
                'vencimento_teste_hidrostatico',
            )
        }),
        ('Localização', {
            'fields': ('predio', 'departamento', 'local', 'ponto_referencia')
        }),
        ('Informações Adicionais', {
            'fields': ('descricao', 'observacoes')
        }),
        ('Mídia', {
            'fields': ('foto', 'qr_code')
        }),
        ('Controle', {
            'fields': ('ativo', 'criado_em', 'atualizado_em')
        }),
    )


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nome', 'descricao', 'ativo', 'criado_em')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome',)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nome', 'responsavel', 'predio', 'localizacao', 'ativo', 'criado_em')
    list_filter = ('empresa', 'ativo', 'predio')
    search_fields = ('nome', 'responsavel', 'email')


@admin.register(Predio)
class PredioAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nome', 'endereco', 'ativo', 'criado_em')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome', 'endereco')


@admin.register(TipoEquipamento)
class TipoEquipamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nome', 'grupo', 'ativo', 'criado_em')
    list_filter = ('empresa', 'ativo', 'grupo')
    search_fields = ('nome',)


@admin.register(TipoServico)
class TipoServicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nome', 'descricao', 'ativo', 'criado_em')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome',)


@admin.register(Periodicidade)
class PeriodicidadeAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nome', 'por_demanda', 'valor', 'tipo', 'ativo', 'criado_em')
    list_filter = ('empresa', 'ativo', 'por_demanda', 'tipo')
    search_fields = ('nome',)


@admin.register(UsuarioPerfil)
class UsuarioPerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_nome_completo', 'tipo_acesso', 'predio', 'departamento', 'status', 'data_criacao')
    list_filter = ('tipo_acesso', 'status', 'predio', 'sites')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    
    def get_nome_completo(self, obj):
        return obj.get_nome_completo()
    get_nome_completo.short_description = 'Nome Completo'


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'destinatario', 'tipo', 'equipamento', 'lida', 'criado_em')
    list_filter = ('tipo', 'lida', 'criado_em', 'empresa')
    search_fields = (
        'titulo',
        'mensagem',
        'destinatario__username',
        'destinatario__email',
        'equipamento__nome',
        'resposta_checklist__item_checklist__pergunta',
    )
    readonly_fields = ('criado_em',)


@admin.register(AlertaChecklist)
class AlertaChecklistAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'equipamento',
        'get_item_pergunta',
        'criado_por',
        'status',
        'resolvido_por',
        'criado_em',
        'resolvido_em',
    )
    list_filter = ('status', 'criado_em', 'resolvido_em', 'empresa')
    search_fields = (
        'equipamento__nome',
        'equipamento__numero_serie',
        'resposta_checklist__item_checklist__pergunta',
        'resposta_checklist__observacao',
        'criado_por__username',
        'criado_por__email',
        'tratativa',
    )
    readonly_fields = (
        'empresa',
        'equipamento',
        'servico',
        'resposta_checklist',
        'criado_por',
        'criado_em',
        'atualizado_em',
        'resolvido_por',
        'resolvido_em',
        'get_item_pergunta',
        'get_observacao_usuario',
        'get_data_checklist',
    )
    fieldsets = (
        ('Alerta', {
            'fields': (
                'status',
                'empresa',
                'equipamento',
                'servico',
                'resposta_checklist',
                'get_item_pergunta',
                'criado_por',
                'get_data_checklist',
                'get_observacao_usuario',
                'criado_em',
            )
        }),
        ('Tratativa', {
            'fields': (
                'tratativa',
                'resolvido_por',
                'resolvido_em',
                'atualizado_em',
            )
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                'empresa',
                'equipamento',
                'servico',
                'criado_por',
                'resolvido_por',
                'resposta_checklist__item_checklist',
            )
        )

    def save_model(self, request, obj, form, change):
        if obj.status == 'resolvido':
            if not obj.resolvido_por_id:
                obj.resolvido_por = request.user
            if not obj.resolvido_em:
                obj.resolvido_em = timezone.now()
        else:
            obj.resolvido_por = None
            obj.resolvido_em = None
        super().save_model(request, obj, form, change)

    @admin.display(description='Item/pergunta')
    def get_item_pergunta(self, obj):
        item = obj.resposta_checklist.item_checklist if obj.resposta_checklist_id else None
        return item.pergunta if item else '-'

    @admin.display(description='Observação do usuário')
    def get_observacao_usuario(self, obj):
        if not obj.resposta_checklist_id:
            return '-'
        return obj.resposta_checklist.observacao or '-'

    @admin.display(description='Data do checklist')
    def get_data_checklist(self, obj):
        if not obj.servico_id:
            return '-'
        return timezone.localtime(obj.servico.criado_em).strftime('%d/%m/%Y %H:%M')

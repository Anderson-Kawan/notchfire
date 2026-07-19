from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from io import BytesIO
from django.core.files import File
from django.utils.text import slugify
from django.utils import timezone
import qrcode

from .tenant_context import get_current_empresa


class Empresa(models.Model):
    nome = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True)
    documento = models.CharField(max_length=40, blank=True, null=True)
    dominio = models.CharField(max_length=120, blank=True, null=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class EmpresaUsuario(models.Model):
    TIPO_ACESSO_CHOICES = [
        ('admin', 'Administrador'),
        ('supervisor', 'Supervisor'),
        ('analista', 'Analista'),
        ('usuario', 'Usuário'),
        ('convidado', 'Convidado'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='empresas',
    )
    tipo_acesso = models.CharField(
        max_length=20,
        choices=TIPO_ACESSO_CHOICES,
        default='usuario',
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Usuário da Empresa'
        verbose_name_plural = 'Usuários das Empresas'
        ordering = ['empresa__nome', 'user__username']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'user'],
                name='unique_empresa_usuario',
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.empresa.nome}"


class EmpresaScopedQuerySet(models.QuerySet):
    def for_empresa(self, empresa):
        if empresa is None:
            return self.none()
        return self.filter(empresa=empresa)

    def sem_empresa(self):
        return self.filter(empresa__isnull=True)


class EmpresaScopedManager(models.Manager.from_queryset(EmpresaScopedQuerySet)):
    def get_queryset(self):
        queryset = super().get_queryset()
        empresa = get_current_empresa()
        if empresa is not None:
            return queryset.filter(empresa=empresa)
        return queryset


class EmpresaScopedModel(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_registros',
    )

    objects = EmpresaScopedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.empresa_id:
            empresa = get_current_empresa()
            if empresa is not None:
                self.empresa = empresa
        super().save(*args, **kwargs)


class Departamento(EmpresaScopedModel):
    """
    Modelo para Departamentos
    """
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    localizacao = models.CharField(max_length=200, blank=True, null=True)
    responsavel = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    predio = models.ForeignKey(
        'Predio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departamentos'
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_departamento_empresa_nome',
            ),
        ]
    
    def __str__(self):
        return self.nome


class Grupo(EmpresaScopedModel):
    """
    Modelo para grupos de equipamentos
    """
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_grupo_empresa_nome',
            ),
        ]
    
    def __str__(self):
        return self.nome
    
    def get_quantidade_equipamentos(self):
        """Retorna a quantidade de equipamentos neste grupo"""
        return self.equipamentos.filter(ativo=True).count()


class Predio(EmpresaScopedModel):
    """
    Modelo para Prédios/Locais
    """
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    endereco = models.CharField(max_length=200, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Prédio'
        verbose_name_plural = 'Prédios'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_predio_empresa_nome',
            ),
        ]
    
    def __str__(self):
        return self.nome
    
    def get_quantidade_departamentos(self):
        """Retorna a quantidade de departamentos no prédio"""
        return self.departamentos.filter(ativo=True).count()


class TipoEquipamento(EmpresaScopedModel):
    """
    Modelo para Tipos de Equipamento
    """
    nome = models.CharField(max_length=100)
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name='tipos_equipamento'
    )
    periodicidade = models.ForeignKey(
        'Periodicidade',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tipos_equipamento'
    )
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tipo de Equipamento'
        verbose_name_plural = 'Tipos de Equipamento'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_tipo_equipamento_empresa_nome',
            ),
        ]

    def __str__(self):
        return f"{self.nome} - {self.grupo.nome}"

    def get_checklist_count(self):
        return ItemChecklist.objects.filter(
            secao__servico_tipo_equipamento__tipo_equipamento=self,
            ativo=True
        ).count()


class ServicoTipoEquipamento(EmpresaScopedModel):
    """
    Modelo para serviços associados a um tipo de equipamento
    """
    tipo_equipamento = models.ForeignKey(
        TipoEquipamento,
        on_delete=models.CASCADE,
        related_name='servicos_configurados'
    )
    tipo_servico = models.ForeignKey(
        'TipoServico',
        on_delete=models.CASCADE,
        related_name='equipamentos_configurados'
    )
    periodicidade = models.ForeignKey(
        'Periodicidade',
        on_delete=models.SET_NULL,
        null=True,
        related_name='servicos_configurados'
    )
    obrigatorio = models.BooleanField(default=True)
    vencimento_final_mes = models.BooleanField(default=False)
    habilitar_assinatura = models.BooleanField(default=False)
    assinatura_obrigatoria = models.BooleanField(default=False)
    acoes_obrigatorias = models.BooleanField(default=False)
    permitir_servicos_massa = models.BooleanField(default=False)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Serviço do Tipo de Equipamento'
        verbose_name_plural = 'Serviços do Tipo de Equipamento'
        ordering = ['ordem', 'tipo_servico__nome']
        unique_together = ['tipo_equipamento', 'tipo_servico', 'periodicidade']

    def __str__(self):
        periodicidade = self.periodicidade.get_rotulo_inspecao() if self.periodicidade else 'SEM PERIODICIDADE'
        return f"{self.tipo_equipamento.nome} - {self.tipo_servico.nome} - {periodicidade}"


class SecaoChecklist(EmpresaScopedModel):
    """
    Modelo para Seções do Checklist de um serviço do tipo de equipamento
    """
    servico_tipo_equipamento = models.ForeignKey(
        'ServicoTipoEquipamento',
        on_delete=models.CASCADE,
        related_name='secoes_checklist',
        null=True,
        blank=True
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seção do Checklist'
        verbose_name_plural = 'Seções do Checklist'
        ordering = ['ordem', 'nome']

    def __str__(self):
        if self.servico_tipo_equipamento:
            return f"{self.nome} - {self.servico_tipo_equipamento}"
        return f"{self.nome} - Sem serviço"


class ItemChecklist(EmpresaScopedModel):
    """
    Modelo para Itens do Checklist
    """
    TIPO_CHOICES = [
        ('sim_nao', 'Sim/Não'),
        ('texto', 'Texto'),
        ('numero', 'Número'),
        ('data', 'Data'),
        ('foto', 'Foto'),
    ]

    secao = models.ForeignKey(
        SecaoChecklist,
        on_delete=models.CASCADE,
        related_name='itens',
        null=True,
        blank=True
    )
    pergunta = models.CharField(max_length=500)
    tipo_resposta = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sim_nao')
    ordem = models.IntegerField(default=0)
    obrigatorio = models.BooleanField(default=True)
    detalhamento = models.TextField(blank=True, null=True, help_text="Instruções para responder a pergunta")
    imagem_descritiva = models.ImageField(upload_to='checklist/', blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Item do Checklist'
        verbose_name_plural = 'Itens do Checklist'
        ordering = ['secao__ordem', 'ordem']

    def __str__(self):
        return f"{self.pergunta[:50]}..."
    



class Periodicidade(EmpresaScopedModel):
    """
    Modelo para Periodicidades de serviços
    """
    TIPO_CHOICES = [
        ('dias', 'Dias'),
        ('semanas', 'Semanas'),
        ('meses', 'Meses'),
        ('anos', 'Anos'),
    ]

    nome = models.CharField(max_length=100)
    por_demanda = models.BooleanField(
        default=False,
        help_text="Por demanda (sem tempo definido)"
    )
    valor = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Valor numérico da periodicidade"
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        blank=True,
        null=True
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Periodicidade'
        verbose_name_plural = 'Periodicidades'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_periodicidade_empresa_nome',
            ),
        ]

    def __str__(self):
        if self.por_demanda:
            return f"{self.nome} - Por Demanda"

        if not self.valor or not self.tipo:
            return self.nome

        return f"{self.nome} - {self.valor} {self.get_tipo_display()}"

    def get_descricao_completa(self):
        """Retorna a descrição completa da periodicidade"""
        if self.por_demanda:
            return "Por Demanda (Sem tempo definido)"

        if not self.valor or not self.tipo:
            return self.nome

        if self.valor == 1:
            if self.tipo == 'dias':
                return "Todos os dias"
            if self.tipo == 'semanas':
                return "Toda semana"
            if self.tipo == 'meses':
                return "Todo mês"
            if self.tipo == 'anos':
                return "Todo ano"

        return f"A cada {self.valor} {self.get_tipo_display().lower()}"

    def get_rotulo_inspecao(self):
        """
        Retorna um rótulo amigável para exibição no cadastro
        e no calendário de inspeções.
        """
        if self.por_demanda:
            return "POR DEMANDA"

        if not self.valor or not self.tipo:
            return self.nome.upper()

        if self.tipo == 'dias':
            if self.valor == 1:
                return "DIÁRIA"
            return f"A CADA {self.valor} DIAS"

        if self.tipo == 'semanas':
            if self.valor == 1:
                return "SEMANAL"
            return f"A CADA {self.valor} SEMANAS"

        if self.tipo == 'meses':
            if self.valor == 1:
                return "MENSAL"
            return f"A CADA {self.valor} MESES"

        if self.tipo == 'anos':
            if self.valor == 1:
                return "ANUAL"
            return f"A CADA {self.valor} ANOS"

        return self.nome.upper()
    
    


class Equipamento(EmpresaScopedModel):
    """
    Modelo para Equipamentos
    """
    # Informações Básicas
    nome = models.CharField(max_length=150, verbose_name="Nome do Equipamento")
    numero_serie = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Série")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    data_fabricacao = models.DateField(blank=True, null=True, verbose_name="Data de Fabricação")
    
    # Relacionamentos
    tipo_equipamento = models.ForeignKey(
        TipoEquipamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipamentos',
        verbose_name="Tipo de Equipamento"
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipamentos',
        verbose_name="Grupo"
    )
    
    # Localização
    predio = models.ForeignKey(
        Predio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipamentos',
        verbose_name="Prédio"
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipamentos',
        verbose_name="Departamento"
    )
    local = models.CharField(max_length=200, blank=True, null=True, verbose_name="Local Específico")
    ponto_referencia = models.CharField(max_length=200, blank=True, null=True, verbose_name="Ponto de Referência")
    
    # Informações adicionais
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    possui_vencimento = models.BooleanField(default=False, verbose_name="Possui vencimento")
    data_vencimento = models.DateField(blank=True, null=True, verbose_name="Data de vencimento")
    vencimento_carga = models.DateField(blank=True, null=True, verbose_name="Vencimento da carga")
    vencimento_teste_hidrostatico = models.DateField(
        blank=True,
        null=True,
        verbose_name="Vencimento do teste hidrostático do casco"
    )
    
    # Mídia
    foto = models.ImageField(upload_to='equipamentos/', blank=True, null=True, verbose_name="Foto")
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True, verbose_name="QR Code")
    
    # Controle
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    # Campos obsoletos (manter para compatibilidade, mas não usar)
    numero_extintor = models.CharField(max_length=50, blank=True, null=True)
    numero_cilindro = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Equipamento'
        verbose_name_plural = 'Equipamentos'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'numero_serie'],
                name='unique_equipamento_empresa_numero_serie',
            ),
        ]
    
    def __str__(self):
        return f"{self.nome} - {self.numero_serie or 'Sem Série'}"

    def is_extintor(self):
        if not self.tipo_equipamento and not self.grupo:
            return False

        tipo_nome = self.tipo_equipamento.nome if self.tipo_equipamento else ''
        grupo = self.grupo or (self.tipo_equipamento.grupo if self.tipo_equipamento else None)
        grupo_nome = grupo.nome if grupo else ''

        return 'extintor' in f'{tipo_nome} {grupo_nome}'.lower()

    def save(self, *args, **kwargs):
        # Mantem o grupo sempre coerente com o tipo selecionado.
        if self.tipo_equipamento:
            self.grupo = self.tipo_equipamento.grupo

        if not self.possui_vencimento:
            self.data_vencimento = None
            self.vencimento_carga = None
            self.vencimento_teste_hidrostatico = None
        elif self.is_extintor():
            self.data_vencimento = None
        else:
            self.vencimento_carga = None
            self.vencimento_teste_hidrostatico = None
        
        super().save(*args, **kwargs)

        if not self.qr_code:
            site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
            qr_data = f"{site_url}/equipamentos/{self.id}/"
            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            file_name = f'equipamento_{self.id}_qrcode.png'
            self.qr_code.save(file_name, File(buffer), save=False)
            super().save(update_fields=['qr_code'])


class Inspecao(EmpresaScopedModel):
    """
    Modelo para Inspeções de Equipamentos
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('realizada', 'Realizada'),
        ('atrasada', 'Atrasada'),
        ('cancelada', 'Cancelada'),
    ]
    
    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name='inspecoes',
        verbose_name="Equipamento"
    )
    periodicidade = models.ForeignKey(
        Periodicidade,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inspecoes',
        verbose_name="Periodicidade"
    )
    nome_inspecao = models.CharField(max_length=200, verbose_name="Nome da Inspeção")
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    data_realizada = models.DateField(blank=True, null=True, verbose_name="Data da Realização")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Inspeção'
        verbose_name_plural = 'Inspeções'
        ordering = ['data_vencimento']
    
    def __str__(self):
        return f"{self.equipamento.nome} - {self.nome_inspecao} - {self.data_vencimento}"
    
    def is_atrasada(self):
        """Verifica se a inspeção está atrasada"""
        from datetime import date
        return self.status == 'pendente' and self.data_vencimento < date.today()


class TipoServico(EmpresaScopedModel):
    """
    Modelo para Tipos de Serviço
    """
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Serviço'
        verbose_name_plural = 'Tipos de Serviço'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_tipo_servico_empresa_nome',
            ),
        ]
    
    def __str__(self):
        return self.nome


class UsuarioPerfil(models.Model):
    """
    Modelo para armazenar informações adicionais do usuário
    """
    
    TIPO_ACESSO_CHOICES = [
        ('admin', 'Administrador'),
        ('supervisor', 'Supervisor'),
        ('analista', 'Analista'),
        ('usuario', 'Usuário'),
        ('convidado', 'Convidado'),
    ]
    
    SITES_CHOICES = [
        ('C3', 'C3'),
        ('C4', 'C4'),
        ('C5', 'C5'),
        ('todos', 'Todos os Sites'),
    ]
    
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('pendente', 'Pendente (Aguardando Convite)'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='perfil'
    )
    
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )

    predio = models.ForeignKey(
        Predio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )

    foto = models.ImageField(
        upload_to='usuarios/',
        blank=True,
        null=True
    )
    
    tipo_acesso = models.CharField(
        max_length=20, 
        choices=TIPO_ACESSO_CHOICES, 
        default='usuario'
    )
    
    sites = models.CharField(
        max_length=20, 
        choices=SITES_CHOICES, 
        default='C3'
    )
    
    filtros = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Filtros adicionais para acesso do usuário"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='ativo'
    )
    
    observacoes = models.TextField(
        blank=True, 
        null=True,
        help_text="Observações adicionais sobre o usuário"
    )
    
    ultimo_acesso = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Data e hora do último acesso do usuário"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'
        ordering = ['-data_criacao']
    
    def __str__(self):
        nome_completo = self.user.get_full_name()
        if nome_completo:
            return f"{nome_completo} - {self.get_tipo_acesso_display()}"
        return f"{self.user.username} - {self.get_tipo_acesso_display()}"
    
    def get_nome_completo(self):
        """Retorna o nome completo do usuário"""
        return self.user.get_full_name() or self.user.username
    
    def is_admin(self):
        """Verifica se o usuário é administrador"""
        return self.tipo_acesso == 'admin'
    
    def is_analista(self):
        """Verifica se o usuário é analista"""
        return self.tipo_acesso == 'analista'

    def is_supervisor(self):
        """Verifica se o usuário é supervisor"""
        return self.tipo_acesso == 'supervisor'
    
    def is_ativo(self):
        """Verifica se o perfil está ativo"""
        return self.status == 'ativo' and self.user.is_active
    
class Servico(EmpresaScopedModel):
    """
    Modelo para Serviços/Inspeções realizadas
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    
    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name='servicos'
    )
    tipo_servico = models.ForeignKey(
        TipoServico,
        on_delete=models.SET_NULL,
        null=True,
        related_name='servicos'
    )
    data_realizacao = models.DateTimeField(auto_now_add=True)
    realizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='servicos_realizados'
    )
    observacoes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    pontuacao_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pontuacao_maxima = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.equipamento.nome} - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"
    
    def calcular_pontuacao_percentual(self):
        if self.pontuacao_maxima > 0:
            return (self.pontuacao_total / self.pontuacao_maxima) * 100
        return 0


class RespostaChecklist(EmpresaScopedModel):
    """
    Modelo para respostas do checklist durante um serviço
    """
    OPCAO_CHOICES = [
        ('atende', 'Atende'),
        ('nao_atende', 'Não atende'),
        ('nao_aplica', 'Não se aplica'),
    ]
    
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='respostas'
    )
    item_checklist = models.ForeignKey(
        ItemChecklist,
        on_delete=models.CASCADE,
        related_name='respostas'
    )
    opcao = models.CharField(max_length=20, choices=OPCAO_CHOICES, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    fotos = models.ImageField(upload_to='servicos/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Resposta do Checklist'
        verbose_name_plural = 'Respostas do Checklist'
    
    def __str__(self):
        return f"{self.servico.equipamento.nome} - {self.item_checklist.pergunta[:50]}"


class Notificacao(EmpresaScopedModel):
    """
    Notificação interna enviada para usuários responsáveis por eventos do sistema.
    """
    TIPO_CHOICES = [
        ('checklist_nao_atende', 'Checklist com item não atende'),
    ]

    destinatario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificacoes',
    )
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificacoes_emitidas',
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=180)
    mensagem = models.TextField()
    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificacoes',
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notificacoes',
    )
    resposta_checklist = models.ForeignKey(
        RespostaChecklist,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificacoes',
    )
    lida = models.BooleanField(default=False)
    lida_em = models.DateTimeField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['destinatario', 'lida', '-criado_em']),
            models.Index(fields=['tipo', '-criado_em']),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.destinatario.username}"


class AlertaChecklist(EmpresaScopedModel):
    """
    Alerta aberto quando uma resposta de checklist é marcada como Não atende.
    """
    STATUS_CHOICES = [
        ('pendente', 'Aguardando tratativa'),
        ('resolvido', 'Resolvido'),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name='alertas_checklist',
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='alertas_checklist',
    )
    resposta_checklist = models.OneToOneField(
        RespostaChecklist,
        on_delete=models.CASCADE,
        related_name='alerta_checklist',
    )
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_checklist_criados',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    tratativa = models.TextField(blank=True, null=True)
    resolvido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_checklist_resolvidos',
    )
    resolvido_em = models.DateTimeField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alerta de Checklist'
        verbose_name_plural = 'Alertas de Checklist'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['status', '-criado_em']),
            models.Index(fields=['criado_por', 'status', '-criado_em']),
        ]

    def __str__(self):
        item = self.resposta_checklist.item_checklist if self.resposta_checklist_id else None
        pergunta = item.pergunta if item else 'Item de checklist'
        return f"{self.equipamento.nome} - {pergunta[:60]}"

    def clean(self):
        super().clean()
        if self.status == 'resolvido' and not (self.tratativa or '').strip():
            raise ValidationError({'tratativa': 'Informe a tratativa realizada antes de resolver o alerta.'})

    def marcar_resolvido(self, usuario, tratativa):
        self.status = 'resolvido'
        self.tratativa = tratativa
        self.resolvido_por = usuario
        self.resolvido_em = timezone.now()
        self.save(update_fields=[
            'status',
            'tratativa',
            'resolvido_por',
            'resolvido_em',
            'atualizado_em',
        ])


class AcaoCorretiva(EmpresaScopedModel):
    """
    Modelo para ações corretivas registradas durante um serviço
    """
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='acoes_corretivas'
    )
    item_checklist = models.ForeignKey(
        ItemChecklist,
        on_delete=models.CASCADE,
        related_name='acoes'
    )
    problema = models.TextField()
    acao = models.TextField()
    responsaveis = models.CharField(max_length=500, help_text="Nomes dos responsáveis")
    prazo = models.DateField()
    anexos = models.FileField(upload_to='acoes_servicos/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Ação Corretiva'
        verbose_name_plural = 'Ações Corretivas'
    
    def __str__(self):
        return f"Ação para {self.servico.equipamento.nome} - {self.item_checklist.pergunta[:50]}"


class RelatorioGerado(EmpresaScopedModel):
    """
    Histórico de relatórios exportados pelo usuário.
    """
    TIPO_CHOICES = [
        ('condensado', 'Relatório Condensado'),
    ]

    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='condensado')
    predio = models.ForeignKey(Predio, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_equipamento = models.ForeignKey(TipoEquipamento, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.SET_NULL, null=True, blank=True)
    equipamento = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    servico = models.ForeignKey(Servico, on_delete=models.SET_NULL, null=True, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    total_servicos = models.IntegerField(default=0)
    total_equipamentos = models.IntegerField(default=0)
    total_nao_conformes = models.IntegerField(default=0)
    media_pontuacao = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    arquivo_nome = models.CharField(max_length=160, blank=True)
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relatorios_gerados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Relatório Gerado'
        verbose_name_plural = 'Relatórios Gerados'
        ordering = ['-criado_em']

    def __str__(self):
        return self.arquivo_nome or f"{self.get_tipo_display()} - {self.criado_em:%d/%m/%Y %H:%M}"

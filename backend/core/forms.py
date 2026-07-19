from django import forms
from .models import (
    Equipamento,
    Grupo,
    Departamento,
    UsuarioPerfil,
    TipoServico,
    Periodicidade,
    TipoEquipamento,
    Predio,
    Inspecao,
    ServicoTipoEquipamento,
    SecaoChecklist,
    ItemChecklist,
)


class EquipamentoForm(forms.ModelForm):
    possui_vencimento = forms.TypedChoiceField(
        choices=[
            ('true', 'Possui vencimento'),
            ('false', 'Não possui vencimento'),
        ],
        coerce=lambda value: value in (True, 'true', 'True', '1', 1),
        empty_value=False,
        initial='false',
        label='Vencimento do equipamento',
        widget=forms.RadioSelect(attrs={'class': 'expiration-radio-input'}),
    )

    class Meta:
        model = Equipamento
        fields = [
            'foto',
            'predio',
            'departamento',
            'grupo',
            'tipo_equipamento',
            'numero_serie',
            'data_fabricacao',
            'marca',
            'possui_vencimento',
            'data_vencimento',
            'vencimento_carga',
            'vencimento_teste_hidrostatico',
            'local',
            'ponto_referencia',
            'ativo',
        ]
        widgets = {
            'data_fabricacao': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'checkbox-input'
            }),
            'data_vencimento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'vencimento_carga': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'vencimento_teste_hidrostatico': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
        labels = {
            'possui_vencimento': 'Vencimento do equipamento',
            'data_vencimento': 'Data de vencimento',
            'vencimento_carga': 'Data de vencimento da carga',
            'vencimento_teste_hidrostatico': 'Data de vencimento do teste hidrostático do casco',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.initial['possui_vencimento'] = 'true' if self.instance.possui_vencimento else 'false'

        self.fields['predio'].queryset = Predio.objects.filter(ativo=True).order_by('nome')
        self.fields['departamento'].queryset = Departamento.objects.filter(ativo=True).order_by('nome')
        self.fields['grupo'].queryset = Grupo.objects.filter(ativo=True).order_by('nome')

        tipo_queryset = TipoEquipamento.objects.filter(ativo=True).select_related('grupo').order_by('nome')
        grupo_id = None
        if self.is_bound:
            grupo_id = self.data.get(self.add_prefix('grupo'))
        elif self.instance and self.instance.pk:
            grupo_id = self.instance.grupo_id

        if grupo_id:
            tipo_queryset = tipo_queryset.filter(grupo_id=grupo_id)
        elif not (self.instance and self.instance.pk and self.instance.tipo_equipamento_id):
            tipo_queryset = tipo_queryset.none()

        self.fields['tipo_equipamento'].queryset = tipo_queryset

        self.fields['predio'].empty_label = 'Selecione um prédio'
        self.fields['departamento'].empty_label = 'Selecione um departamento'
        self.fields['grupo'].empty_label = 'Selecione um grupo'
        self.fields['tipo_equipamento'].empty_label = 'Selecione um tipo de equipamento'
        self.fields['grupo'].required = True
        self.fields['tipo_equipamento'].required = True

        campos = [
            'predio',
            'departamento',
            'grupo',
            'tipo_equipamento',
            'numero_serie',
            'data_fabricacao',
            'marca',
            'data_vencimento',
            'vencimento_carga',
            'vencimento_teste_hidrostatico',
            'local',
            'ponto_referencia',
        ]

        for campo in campos:
            classes = self.fields[campo].widget.attrs.get('class', '')
            self.fields[campo].widget.attrs['class'] = f'{classes} form-control'.strip()

        self.fields['numero_serie'].widget.attrs.update({
            'placeholder': 'Número de série'
        })
        self.fields['marca'].widget.attrs.update({
            'placeholder': 'Marca de fabricação'
        })
        self.fields['local'].widget.attrs.update({
            'placeholder': 'Especificação do equipamento'
        })
        self.fields['ponto_referencia'].widget.attrs.update({
            'placeholder': 'Ponto de referência'
        })

        self.fields['foto'].widget.attrs.update({
            'class': 'file-input',
            'accept': '.jpg,.jpeg,.png,.gif'
        })

    def clean(self):
        cleaned_data = super().clean()
        grupo = cleaned_data.get('grupo')
        tipo_equipamento = cleaned_data.get('tipo_equipamento')
        possui_vencimento = cleaned_data.get('possui_vencimento')
        data_vencimento = cleaned_data.get('data_vencimento')
        vencimento_carga = cleaned_data.get('vencimento_carga')
        vencimento_teste_hidrostatico = cleaned_data.get('vencimento_teste_hidrostatico')

        if grupo and tipo_equipamento and tipo_equipamento.grupo_id != grupo.id:
            self.add_error('tipo_equipamento', 'Selecione um tipo vinculado ao grupo escolhido.')

        is_extintor = bool(
            tipo_equipamento and 'extintor' in (
                f'{tipo_equipamento.nome} {tipo_equipamento.grupo.nome if tipo_equipamento.grupo else ""}'
            ).lower()
        )

        if possui_vencimento:
            if is_extintor:
                if not vencimento_carga:
                    self.add_error('vencimento_carga', 'Informe o vencimento da carga.')
                if not vencimento_teste_hidrostatico:
                    self.add_error(
                        'vencimento_teste_hidrostatico',
                        'Informe o vencimento do teste hidrostático do casco.'
                    )
                cleaned_data['data_vencimento'] = None
            else:
                if not data_vencimento:
                    self.add_error('data_vencimento', 'Informe a data de vencimento do equipamento.')
                cleaned_data['vencimento_carga'] = None
                cleaned_data['vencimento_teste_hidrostatico'] = None
        else:
            cleaned_data['data_vencimento'] = None
            cleaned_data['vencimento_carga'] = None
            cleaned_data['vencimento_teste_hidrostatico'] = None

        return cleaned_data

    def save(self, commit=True):
        equipamento = super().save(commit=False)

        if not equipamento.numero_serie:
            equipamento.numero_serie = None
        if not equipamento.numero_extintor:
            equipamento.numero_extintor = None

        if equipamento.tipo_equipamento:
            equipamento.grupo = equipamento.tipo_equipamento.grupo

        if not equipamento.nome:
            codigo = equipamento.numero_serie or equipamento.numero_extintor or ''
            tipo_nome = equipamento.tipo_equipamento.nome if equipamento.tipo_equipamento else 'Equipamento'
            equipamento.nome = f'{tipo_nome} {codigo}'.strip()

        if commit:
            equipamento.save()
            self.save_m2m()

        return equipamento


class GrupoForm(forms.ModelForm):
    class Meta:
        model = Grupo
        fields = ['nome', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Extintores, Hidrantes, etc.'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do grupo'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.upper().strip()
            instance = getattr(self, 'instance', None)
            queryset = Grupo.objects.filter(nome=nome)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Já existe um grupo com este nome.')
        return nome


class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nome', 'descricao', 'localizacao', 'responsavel', 'email', 'telefone', 'predio', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: RH, TI, Financeiro, etc.'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do departamento'
            }),
            'localizacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Localização do departamento'
            }),
            'responsavel': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do responsável'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@departamento.com'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'predio': forms.Select(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['predio'].queryset = Predio.objects.filter(ativo=True).order_by('nome')
        self.fields['predio'].empty_label = 'Selecione um prédio'

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.upper().strip()
            instance = getattr(self, 'instance', None)
            queryset = Departamento.objects.filter(nome=nome)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Já existe um departamento com este nome.')
        return nome


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = UsuarioPerfil
        fields = ['foto', 'predio', 'departamento', 'tipo_acesso', 'sites', 'filtros', 'status', 'observacoes']
        widgets = {
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'predio': forms.Select(attrs={'class': 'form-control'}),
            'departamento': forms.Select(attrs={'class': 'form-control'}),
            'tipo_acesso': forms.Select(attrs={'class': 'form-control'}),
            'sites': forms.Select(attrs={'class': 'form-control'}),
            'filtros': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filtros adicionais'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observações...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['predio'].queryset = Predio.objects.filter(ativo=True).order_by('nome')
        self.fields['predio'].empty_label = 'Selecione um prédio'
        self.fields['departamento'].queryset = Departamento.objects.filter(ativo=True).order_by('nome')
        self.fields['departamento'].empty_label = 'Selecione um departamento'


class TipoServicoForm(forms.ModelForm):
    class Meta:
        model = TipoServico
        fields = ['nome', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Manutenção, Instalação, Inspeção, etc.'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do tipo de serviço'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.upper().strip()
            instance = getattr(self, 'instance', None)
            queryset = TipoServico.objects.filter(nome=nome)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Já existe um tipo de serviço com este nome.')
        return nome


class PeriodicidadeForm(forms.ModelForm):
    class Meta:
        model = Periodicidade
        fields = ['nome', 'por_demanda', 'valor', 'tipo', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Diária, Semanal, Mensal, Anual'
            }),
            'por_demanda': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1',
                'min': 1
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        por_demanda = cleaned_data.get('por_demanda')
        valor = cleaned_data.get('valor')
        tipo = cleaned_data.get('tipo')

        if not por_demanda:
            if not valor:
                self.add_error('valor', 'O valor é obrigatório quando não for por demanda.')
            if not tipo:
                self.add_error('tipo', 'O tipo é obrigatório quando não for por demanda.')

        return cleaned_data

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.strip().upper()
            instance = getattr(self, 'instance', None)
            queryset = Periodicidade.objects.filter(nome=nome)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Já existe uma periodicidade com este nome.')
        return nome


class InspecaoForm(forms.ModelForm):
    class Meta:
        model = Inspecao
        fields = ['periodicidade', 'nome_inspecao', 'data_vencimento', 'observacoes']
        widgets = {
            'periodicidade': forms.Select(attrs={'class': 'form-control'}),
            'nome_inspecao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Inspeção Mensal'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações da inspeção'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['periodicidade'].queryset = Periodicidade.objects.filter(ativo=True).order_by('nome')
        self.fields['periodicidade'].empty_label = 'Selecione uma periodicidade'


class PredioForm(forms.ModelForm):
    class Meta:
        model = Predio
        fields = ['nome', 'descricao', 'endereco', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Prédio C3, Prédio Administrativo, etc.'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do prédio'
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Endereço completo do prédio'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.strip()
            instance = getattr(self, 'instance', None)
            queryset = Predio.objects.filter(nome=nome)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Já existe um prédio com este nome.')
        return nome


class TipoEquipamentoForm(forms.ModelForm):
    class Meta:
        model = TipoEquipamento
        fields = ['nome', 'grupo', 'periodicidade', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Extintor ABC, Mangueira, Sirene'
            }),
            'grupo': forms.Select(attrs={'class': 'form-control'}),
            'periodicidade': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do tipo de equipamento'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grupo'].queryset = Grupo.objects.filter(ativo=True).order_by('nome')
        self.fields['grupo'].empty_label = 'Selecione um grupo'
        self.fields['periodicidade'].queryset = Periodicidade.objects.filter(ativo=True).order_by('nome')
        self.fields['periodicidade'].empty_label = 'Selecione uma periodicidade'

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.strip().upper()
            instance = getattr(self, 'instance', None)
            queryset = TipoEquipamento.objects.filter(nome=nome)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Já existe um tipo de equipamento com este nome.')
        return nome


class ServicoTipoEquipamentoForm(forms.ModelForm):
    class Meta:
        model = ServicoTipoEquipamento
        fields = [
            'tipo_servico',
            'periodicidade',
            'obrigatorio',
            'vencimento_final_mes',
            'habilitar_assinatura',
            'assinatura_obrigatoria',
            'acoes_obrigatorias',
            'permitir_servicos_massa',
            'ativo',
        ]
        widgets = {
            'tipo_servico': forms.Select(attrs={'class': 'form-control'}),
            'periodicidade': forms.Select(attrs={'class': 'form-control'}),
            'obrigatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vencimento_final_mes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'habilitar_assinatura': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assinatura_obrigatoria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acoes_obrigatorias': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permitir_servicos_massa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_servico'].queryset = TipoServico.objects.filter(ativo=True).order_by('nome')
        self.fields['periodicidade'].queryset = Periodicidade.objects.filter(ativo=True).order_by('nome')
        self.fields['tipo_servico'].empty_label = 'Selecione um tipo de serviço'
        self.fields['periodicidade'].empty_label = 'Selecione uma periodicidade'


class SecaoChecklistForm(forms.ModelForm):
    class Meta:
        model = SecaoChecklist
        fields = ['nome', 'descricao', 'ordem', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da seção'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição da seção'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ItemChecklistForm(forms.ModelForm):
    class Meta:
        model = ItemChecklist
        fields = [
            'secao',
            'pergunta',
            'tipo_resposta',
            'ordem',
            'obrigatorio',
            'detalhamento',
            'imagem_descritiva',
            'ativo',
        ]
        widgets = {
            'secao': forms.Select(attrs={'class': 'form-control'}),
            'pergunta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite a pergunta'}),
            'tipo_resposta': forms.Select(attrs={'class': 'form-control'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'obrigatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'detalhamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Instruções para responder'}),
            'imagem_descritiva': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        servico_tipo_equipamento = kwargs.pop('servico_tipo_equipamento', None)
        super().__init__(*args, **kwargs)

        if servico_tipo_equipamento:
            self.fields['secao'].queryset = SecaoChecklist.objects.filter(
                servico_tipo_equipamento=servico_tipo_equipamento,
                ativo=True
            ).order_by('ordem', 'nome')
        else:
            self.fields['secao'].queryset = SecaoChecklist.objects.none()

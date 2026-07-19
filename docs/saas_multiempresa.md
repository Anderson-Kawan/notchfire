# SaaS multiempresa - auditoria e plano inicial

Data da auditoria: 2026-06-06

## Escopo desta fase

Esta fase documenta a camada SaaS multiempresa proposta para o NotchFire, usando:

- banco de dados compartilhado;
- schema compartilhado;
- isolamento por coluna `empresa_id`.

Na fase documental original, nenhum model foi alterado e nenhuma migration foi
criada. Em 2026-06-08, a base multiempresa inicial foi implementada.

## Estado implementado em 2026-06-08

Models adicionados:

- `Empresa`
- `EmpresaUsuario`

Models de negocio com `empresa` nullable:

- `Predio`
- `Departamento`
- `Grupo`
- `Periodicidade`
- `TipoEquipamento`
- `TipoServico`
- `ServicoTipoEquipamento`
- `SecaoChecklist`
- `ItemChecklist`
- `Equipamento`
- `Inspecao`
- `Servico`
- `RespostaChecklist`
- `AcaoCorretiva`
- `RelatorioGerado`

Migrations adicionadas:

- `0012_empresa_empresausuario_alter_departamento_nome_and_more.py`
- `0013_backfill_empresa_padrao.py`

Comportamento implementado:

- migration de backfill cria `Empresa Padrao`;
- registros existentes recebem `empresa=Empresa Padrao`;
- usuarios existentes recebem vinculo em `EmpresaUsuario`;
- middleware web resolve empresa ativa por sessao/vinculo;
- APIs DRF com token ativam empresa depois da autenticacao;
- managers dos models de negocio filtram pela empresa ativa quando ela existe;
- novos registros tenant-aware recebem empresa ativa automaticamente no `save`;
- `Grupo`, `Departamento`, `Predio`, `Periodicidade`, `TipoEquipamento`, `TipoServico` e `Equipamento.numero_serie` usam constraints por empresa.

Limites ainda existentes:

- a UI de selecao/troca de empresa ainda nao foi criada;
- `UsuarioPerfil` ainda existe como perfil legado e precisa ser conciliado com `EmpresaUsuario`;
- views e forms ainda devem ser revisados em detalhe para selects relacionais e validacoes especificas por empresa;
- os campos `empresa` continuam nullable ate uma fase posterior de endurecimento.

## Linha de base executada

Comandos executados em `backend/` antes da documentação:

```bash
./venv/bin/python manage.py check
./venv/bin/python manage.py test
./venv/bin/python manage.py showmigrations
./venv/bin/python manage.py shell -c "print('Django shell OK')"
```

Resultados:

- `check`: passou, sem issues.
- `test`: passou, 4 testes executados.
- `showmigrations`: migrations aplicadas em `core` até `0011_relatoriogerado_equipamento`.
- `shell`: carregou o ambiente Django e exibiu `Django shell OK`.

Backup criado antes de qualquer mudança documental:

```text
backups/db.sqlite3.20260606_030706.bak
```

## Arquivos auditados

Arquivos obrigatórios lidos:

- `backend/core/models.py`
- `backend/core/views.py`
- `backend/core/views_api.py`
- `backend/core/urls.py`
- `backend/core/urls_api.py`
- `backend/core/serializers.py`
- `backend/core/admin.py`
- `backend/core/migrations/0001_initial.py` ate `0011_relatoriogerado_equipamento.py`

Arquivo adicional consultado por risco de selects e validacoes globais:

- `backend/core/forms.py`

## Models existentes

Models atuais em `backend/core/models.py`:

- `Departamento`: cadastro de departamento, com vinculo opcional a `Predio`.
- `Grupo`: agrupamento de equipamentos.
- `Predio`: cadastro de predios/locais.
- `TipoEquipamento`: tipo de equipamento, vinculado a `Grupo` e `Periodicidade`.
- `ServicoTipoEquipamento`: configuracao de servicos por tipo de equipamento.
- `SecaoChecklist`: secao de checklist vinculada a `ServicoTipoEquipamento`.
- `ItemChecklist`: pergunta/item de checklist.
- `Periodicidade`: regra de recorrencia dos servicos.
- `Equipamento`: equipamento fisico, com predio, departamento, grupo, tipo e QR Code.
- `Inspecao`: inspecao planejada/realizada de equipamento.
- `TipoServico`: tipo de servico/checklist.
- `UsuarioPerfil`: perfil complementar do usuario Django.
- `Servico`: servico/checklist realizado ou rascunho.
- `RespostaChecklist`: resposta de item de checklist.
- `AcaoCorretiva`: acao corretiva vinculada a servico e item.
- `RelatorioGerado`: historico de relatorios exportados.

## Models que precisam de `empresa`

Para isolamento por coluna, a lista principal da Fase 3 deve receber `empresa = ForeignKey(Empresa, ...)`, inicialmente nullable:

- `Predio`
- `Departamento`
- `Grupo`
- `Periodicidade`
- `TipoEquipamento`
- `TipoServico`
- `ServicoTipoEquipamento`
- `SecaoChecklist`
- `ItemChecklist`
- `Equipamento`
- `Inspecao`
- `Servico`
- `RespostaChecklist`
- `AcaoCorretiva`
- `RelatorioGerado`

Observacao: `UsuarioPerfil` nao esta na lista da Fase 3, mas precisa entrar no desenho de acesso. Hoje ele guarda `predio`, `departamento`, `tipo_acesso`, `sites` e `status`. Na camada SaaS, o acesso deve vir de `EmpresaUsuario`, e qualquer uso de `UsuarioPerfil` deve ser revisado para nao criar permissao paralela ou vazamento entre empresas.

## Queries que precisam de filtro por empresa

### `models.py`

- `Grupo.get_quantidade_equipamentos()` usa `self.equipamentos.filter(ativo=True)`. Depois de `empresa`, deve garantir que o grupo e seus equipamentos pertencem a mesma empresa.
- `Predio.get_quantidade_departamentos()` usa `self.departamentos.filter(ativo=True)`. Deve permanecer restrito ao predio/empresa.
- `TipoEquipamento.get_checklist_count()` usa `ItemChecklist.objects.filter(...)`. Deve filtrar por empresa ou por cadeia `secao -> servico_tipo_equipamento -> tipo_equipamento -> empresa`.
- `Equipamento.save()` gera QR Code com URL local por ID. A resolucao por QR deve ser sempre validada por empresa no endpoint, pois ID bruto pode identificar equipamento de outra empresa.
- `Servico`, `RespostaChecklist`, `AcaoCorretiva` e `RelatorioGerado` acessam dados por relacoes; as fases seguintes devem garantir consistencia de empresa entre todos os relacionamentos.

### `views.py` - usuarios e perfis

- `criar_usuario_view` carrega `Predio.objects.filter(ativo=True)` para select.
- `api_usuarios_listar` usa `User.objects.select_related('perfil').all()` e filtros em `UsuarioPerfil`.
- `api_usuarios_criar`, `api_usuarios_detalhe` e `minha_conta_view` criam/alteram `User` e `UsuarioPerfil`.
- Na camada SaaS, usuarios devem ser listados por `EmpresaUsuario` da empresa ativa. Superusuarios podem ter uma visao global explicita.

### `views.py` - equipamentos

- `api_equipamentos_listar` usa `Equipamento.objects.select_related(...).all()`, busca, contagens e filtros.
- `equipamentos_view` usa `Equipamento.objects.all().order_by('-id')`.
- `detalhe_equipamento_view` busca equipamento por ID, servicos configurados, ultimos servicos, contagens, tipos, departamentos e predios.
- `editar_equipamento_view`, `api_equipamento_detalhes`, `api_equipamento_editar_detalhe`, `api_equipamento_toggle_ativo`, `api_equipamento_upload_foto` e `api_equipamento_excluir` buscam por ID sem empresa.
- `api_equipamentos_para_servico` lista equipamentos ativos para execucao de servico.
- Validacao de `numero_serie` em `api_equipamento_editar_detalhe` ainda e global.

### `views.py` - grupos, departamentos, predios

- `api_grupos_listar`, `api_grupos_criar`, `api_grupos_editar`, `api_grupos_excluir` usam queries globais em `Grupo` e contagens globais em `Equipamento`.
- `api_departamentos_listar`, `api_departamentos_criar`, `api_departamentos_editar`, `api_departamentos_excluir`, `api_departamentos_para_select` e `api_departamentos_por_predio` usam queries globais em `Departamento` e `Predio`.
- `api_predios_listar`, `api_predios_criar`, `api_predios_editar`, `api_predios_para_select` e `api_predios_excluir` usam queries globais em `Predio` e `Departamento`.
- As validacoes de nome unico para `Grupo`, `Departamento` e `Predio` sao globais e devem virar escopo por empresa.

### `views.py` - tipo de servico, periodicidade e tipo de equipamento

- `api_tipos_servico_listar`, `api_tipos_servico_criar`, `api_tipos_servico_editar`, `api_tipos_servico_excluir` usam `TipoServico` e `ServicoTipoEquipamento` sem empresa.
- `api_periodicidades_listar`, `api_periodicidades_criar`, `api_periodicidades_editar`, `api_periodicidades_excluir`, `periodicidades_para_select` e `api_periodicidades_para_select` usam `Periodicidade`, `TipoEquipamento` e `ServicoTipoEquipamento` sem empresa.
- `api_tipos_equipamento_listar`, `api_tipos_equipamento_criar`, `api_tipo_equipamento_info`, `api_tipos_equipamento_editar`, `api_tipos_equipamento_excluir`, `api_tipo_equipamento_detalhe` e selects relacionados usam `TipoEquipamento`, `Grupo` e `Periodicidade` sem empresa.
- Validacoes de nome unico em `TipoServico`, `Periodicidade` e `TipoEquipamento` sao globais.

### `views.py` - editor de servicos e checklist

- `detalhe_tipo_equipamento_view` busca `TipoEquipamento`, `ServicoTipoEquipamento`, `Grupo`, `TipoServico`, `Periodicidade` e `ItemChecklist` sem empresa.
- `api_editor_servico_criar`, `api_editor_servico_detalhes`, `api_editor_servico_editar`, `api_editor_servico_excluir` e `api_editor_checklist_apagar` precisam restringir `ServicoTipoEquipamento`.
- `api_editor_secao_*`, `api_editor_item_*` e `api_checklist_item_*` precisam restringir `SecaoChecklist` e `ItemChecklist`.
- Rotas legadas do editor no final do arquivo usam `get_object_or_404` por ID em `TipoEquipamento`, `ServicoTipoEquipamento`, `SecaoChecklist` e `ItemChecklist`.
- Risco existente: algumas funcoes legadas ainda referenciam `SecaoChecklist.tipo_equipamento`, campo que nao existe no model atual. Isso nao foi alterado nesta fase, mas deve ser considerado antes de apoiar a camada SaaS nesses endpoints.

### `views.py` - calendario

- `_calendario_queryset_equipamentos` lista `Equipamento.objects.filter(ativo=True)`.
- `_calendario_queryset_configs` lista `ServicoTipoEquipamento` por tipos de equipamento.
- `_calendario_eventos_data` busca `Servico.objects.filter(status='concluido', equipamento_id__in=...)` e ultimos servicos anteriores.
- `api_calendario_filtros` lista `Predio`, `Departamento`, `Grupo`, `TipoEquipamento`, `ServicoTipoEquipamento` e `User` sem empresa.
- `api_calendario_eventos` e `exportar_calendario_dados` dependem de `_calendario_eventos_data`, portanto precisam receber empresa ativa.

### `views.py` - servicos, rascunhos e acoes corretivas

- `api_servicos_listar` usa `Servico.objects.select_related(...).all()` e contagens globais.
- `api_servicos_criar` busca `Equipamento`, `TipoServico`, rascunhos, `ItemChecklist` e cria `Servico`/`RespostaChecklist` sem empresa.
- `api_servicos_detalhes`, `api_servicos_rascunho`, `api_servicos_descartar`, `_total_itens_checklist`, `api_rascunhos_listar` e `api_servicos_atualizar` precisam filtrar por empresa alem de usuario/status.
- `api_tipos_servico_para_equipamento` e `api_checklist_itens_por_tipo` resolvem configuracoes por equipamento/tipo sem empresa.
- `api_acoes_corretivas_criar` cria `AcaoCorretiva` por IDs recebidos em POST; deve validar se `servico` e `item_checklist` pertencem a empresa ativa antes de salvar.

### `views.py` - relatorios

- `_relatorios_queryset` busca `Servico.objects.filter(status='concluido')`, com filtros por predio, tipo, servico, equipamento e periodo.
- `_relatorio_metricas` calcula contagens sobre o queryset recebido.
- `api_relatorios_filtros` lista `Predio`, `TipoEquipamento`, `Equipamento` e `ServicoTipoEquipamento` sem empresa.
- `api_relatorios_resumo` depende de `_relatorios_queryset`.
- `exportar_relatorio_condensado` cria `RelatorioGerado` com filtros por IDs, sem empresa.
- `api_relatorios_historico` filtra apenas por `criado_por=request.user`; um usuario multiempresa poderia ver historico de outra empresa se nao houver `empresa`.
- `baixar_relatorio_gerado` tambem filtra por usuario, mas precisa filtrar por empresa.

### `views_api.py` - DRF/mobile

- `_tipos_servico_equipamento` lista `ServicoTipoEquipamento` por tipo de equipamento.
- `QRCodeEquipamentoAPI` resolve equipamento por QR/ID e precisa validar empresa ativa, pois QR pode conter ID bruto ou URL `/equipamentos/<id>/`.
- `EquipamentoTiposServicoAPI` busca equipamento por ID.
- `ChecklistItensAPI` busca `TipoEquipamento`, `TipoServico`, `ServicoTipoEquipamento`, secoes e itens.
- `ServicoCriarAPI` busca `Equipamento`, `TipoServico`, valida configuracao e cria `Servico`/`RespostaChecklist`.
- `EquipamentoViewSet` usa `Equipamento.objects.all().order_by('-id')`.
- `DashboardAPI` usa `_calendario_eventos_data`, `Servico`, `Equipamento` e `AcaoCorretiva` sem empresa.

### `admin.py`

O admin atual registra `Equipamento`, `Grupo`, `Departamento`, `Predio`, `TipoEquipamento`, `TipoServico`, `Periodicidade` e `UsuarioPerfil` com querysets globais. Depois da camada SaaS:

- incluir `Empresa`, `EmpresaUsuario` no admin;
- adicionar `empresa` em `list_display` e `list_filter` dos models de negocio;
- sobrescrever `get_queryset` para usuarios nao superuser;
- preencher `empresa` automaticamente quando possivel;
- impedir que relacionamentos de outra empresa aparecam em selects.

### `serializers.py`

`EquipamentoSerializer` usa `fields = '__all__'`. Quando `empresa` for adicionado, deve-se decidir se o campo sera somente leitura, omitido do payload mobile, ou preenchido pelo contexto da request.

### `urls.py` e `urls_api.py`

Nao ha queries diretas relevantes, mas estes arquivos expõem todas as superficies que precisarão de filtro:

- web HTML;
- endpoints AJAX internos;
- endpoints DRF/mobile;
- endpoints duplicados antigos e mobile para servicos/checklist/QR.

### `forms.py`

Embora nao esteja na lista obrigatoria da fase, ele usa querysets globais para selects e validacoes:

- selects de `Predio`, `Departamento`, `TipoEquipamento`, `Grupo`, `TipoServico`, `Periodicidade` e `SecaoChecklist`;
- validacoes de nome unico globais em `Grupo`, `Departamento`, `TipoServico`, `Periodicidade`, `Predio` e `TipoEquipamento`.

## Plano de migrations

### Fase 2

Criar os models:

- `Empresa`
- `EmpresaUsuario`

Registrar ambos no admin.

Migration esperada:

- `0012_empresa_empresausuario.py` ou nome equivalente gerado pelo Django.

Testes esperados:

- criar empresa;
- criar vinculo usuario-empresa;
- impedir vinculo duplicado;
- permitir o mesmo usuario em duas empresas diferentes.

### Fase 3

Adicionar `empresa` nullable e blank nos models de negocio listados, com `related_name` explicito.

Migration esperada:

- migration incremental adicionando `empresa` como nullable.

Importante:

- nao tornar `empresa` obrigatoria antes do backfill;
- nao remover campos legados;
- nao mudar constraints globais na mesma migration se isso dificultar rollback.

### Fases seguintes recomendadas

- Criar UI/API de selecao e troca de empresa ativa.
- Conciliar `UsuarioPerfil.tipo_acesso` com `EmpresaUsuario.tipo_acesso`.
- Revisar forms e selects relacionais para impedir escolhas entre empresas diferentes.
- Criar testes de isolamento para endpoints web, AJAX, DRF/mobile, relatorios e calendario.
- Revisar endpoints legados do editor antes de depender deles para SaaS.
- Somente depois de backfill, testes e revisao de endpoints, avaliar tornar `empresa` obrigatoria nos models centrais.

## Rollback

Rollback documental desta fase:

- remover `docs/saas_multiempresa.md`, se necessario.
- o backup do SQLite pode permanecer como evidencia de seguranca.

Rollback das proximas fases:

- antes de migrar, manter novo backup de `backend/db.sqlite3`;
- para desfazer somente criacao de `Empresa`/`EmpresaUsuario`, usar `./venv/bin/python manage.py migrate core 0011` se a migration da Fase 2 for a proxima e ainda nao houver dependencias de dados;
- para migrations com `empresa` nullable, garantir que a operacao reversa remova apenas os campos adicionados;
- para data migrations, implementar reverse code que desfaca o vinculo legado sem apagar registros de negocio;
- nunca usar `flush`, `DROP DATABASE`, `TRUNCATE` ou apagamento manual de dados.

## Riscos e pendencias

- A aplicacao possui empresa ativa por middleware/API, mas ainda nao possui UI de troca.
- Usuarios podem pertencer a mais de uma empresa; sem selecao manual, o primeiro vinculo ativo e usado.
- Superusuarios com vinculo ativo tambem entram no tenant; sem vinculo ativo, ficam sem filtro global.
- Algumas validacoes de forms/views ainda precisam de revisao alem das constraints principais por empresa.
- QR Code por ID pode expor equipamento de outra empresa se o endpoint nao filtrar por empresa.
- Relatorios historicos hoje sao filtrados por usuario, nao por empresa.
- Admin Django e serializers foram iniciados, mas forms ainda podem precisar de ajustes em selects.
- Campos `empresa` continuam nullable; exigir `NOT NULL` cedo ainda quebraria fluxos incompletos.
- A migracao real para PostgreSQL deve ser executada em servidor PostgreSQL acessivel.
- Ha endpoints legados do editor que parecem referenciar campo removido de `SecaoChecklist`; isso deve ser corrigido ou isolado antes de depender deles para SaaS.

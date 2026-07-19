# Arquitetura do projeto Django - NotchFire

Gerado em: 2026-06-04

## Escopo da analise

Esta documentacao cobre o backend Django localizado em `backend/`.
Tambem foi feita uma leitura pontual de `mobile/` apenas para entender os pontos que podem dificultar a criacao e estabilizacao da API mobile.

Nenhum codigo da aplicacao foi alterado nesta analise. Foi criado apenas este arquivo de documentacao.

## Resumo executivo

O projeto e um Django monolitico pequeno, com quase todo o dominio concentrado no app `core`. O backend atende tres superficies ao mesmo tempo:

- Paginas HTML renderizadas por templates Django.
- Endpoints JSON internos usados pelo frontend web, definidos em `core.views` e montados em rotas como `/api/equipamentos/`.
- Endpoints DRF com Token Authentication, definidos em `core.views_api` e montados tambem sob `/api/`.

O principal ponto arquitetural de atencao e que o prefixo `/api/` esta compartilhado pelas APIs internas de sessao e pela API DRF. Como `core.urls` e incluido antes de `core.urls_api`, algumas rotas DRF ficam sombreadas por rotas internas, especialmente `/api/equipamentos/` e `/api/equipamentos/<id>/`.

O modelo de dados ja esta relativamente rico para inventario, checklist, servicos, relatorios e usuarios, mas ainda ha sinais de evolucao rapida: campos obsoletos, modelos pouco usados, codigo legado no final de `views.py`, validacoes repetidas em views/forms e pouca separacao entre regra de negocio, serializacao e apresentacao.

## Estrutura do projeto

Estrutura relevante encontrada:

```text
.
|-- README.md
|-- docs/
|   |-- arquitetura.md
|   `-- iniciar.md
|-- backend/
|   |-- manage.py
|   |-- db.sqlite3
|   |-- media/
|   |   |-- equipamentos/
|   |   |-- qrcodes/
|   |   `-- usuarios/
|   |-- venv/
|   |-- notchfire_project/
|   |   |-- __init__.py
|   |   |-- asgi.py
|   |   |-- settings.py
|   |   |-- urls.py
|   |   `-- wsgi.py
|   `-- core/
|       |-- __init__.py
|       |-- admin.py
|       |-- apps.py
|       |-- forms.py
|       |-- models.py
|       |-- serializers.py
|       |-- tests.py
|       |-- urls.py
|       |-- urls_api.py
|       |-- views.py
|       |-- views_api.py
|       |-- migrations/
|       |-- static/core/
|       |   |-- css/
|       |   |-- img/
|       |   `-- js/
|       `-- templates/core/
`-- mobile/
    |-- package.json
    `-- src/
        |-- context/
        |-- navigation/
        |-- screens/
        |-- services/
        |-- styles/
        `-- theme/
```

Arquivos centrais do backend:

- `backend/notchfire_project/settings.py`: configuracoes globais, apps, banco SQLite, DRF e media/static.
- `backend/notchfire_project/urls.py`: inclui `core.urls` na raiz e `core.urls_api` em `/api/`.
- `backend/core/models.py`: todo o modelo de dominio.
- `backend/core/views.py`: views HTML, endpoints JSON internos, calendario, servicos, relatorios e geracao manual de PDF.
- `backend/core/views_api.py`: API DRF usada pelo mobile.
- `backend/core/urls.py`: rotas web e endpoints JSON internos.
- `backend/core/urls_api.py`: rotas DRF e router de equipamentos.
- `backend/core/static/core/js/`: consumidores web dos endpoints internos.
- `mobile/src/services/api.ts`: base URL mobile hardcoded para `http://127.0.0.1:8000/api/`.

## Configuracao Django

Configuracao observada em `settings.py`:

- Django gerado com `Django 6.0.3`.
- `DEBUG = True`.
- `SECRET_KEY` hardcoded no arquivo.
- `ALLOWED_HOSTS` limitado a `localhost`, `127.0.0.1`, `.ngrok-free.app` e `.ngrok-free.dev`.
- `CSRF_TRUSTED_ORIGINS` configurado para ngrok.
- `USE_X_FORWARDED_HOST`, `USE_X_FORWARDED_PORT` e `SECURE_PROXY_SSL_HEADER` habilitados para proxy/ngrok.
- Banco atual: SQLite em `BASE_DIR / 'db.sqlite3'`.
- `LANGUAGE_CODE = 'pt-br'`.
- `TIME_ZONE = 'UTC'`.
- `STATIC_URL = 'static/'`.
- `MEDIA_URL = '/media/'`.
- `MEDIA_ROOT = BASE_DIR / 'media'`.
- DRF com `TokenAuthentication` e permissao padrao `IsAuthenticated`.

Observacoes:

- Nao ha `requirements.txt`, `pyproject.toml`, `Pipfile`, Dockerfile, `docker-compose` ou `.env` encontrados no backend.
- `MEDIA_URL` e servido em modo debug tanto em `backend/notchfire_project/urls.py` quanto no final de `core/urls.py`, gerando duplicidade de configuracao de media em desenvolvimento.

## Aplicativos Django existentes

Apps em `INSTALLED_APPS`:

| App | Tipo | Funcao |
| --- | --- | --- |
| `django.contrib.admin` | Django contrib | Admin Django. |
| `django.contrib.auth` | Django contrib | Usuarios, grupos, permissoes e autenticacao. |
| `django.contrib.contenttypes` | Django contrib | Content types do Django. |
| `django.contrib.sessions` | Django contrib | Sessao web. |
| `django.contrib.messages` | Django contrib | Mensagens em views HTML. |
| `django.contrib.staticfiles` | Django contrib | Arquivos estaticos. |
| `rest_framework` | Terceiro | Django REST Framework. |
| `rest_framework.authtoken` | Terceiro | Tokens persistidos para API mobile. |
| `core` | Local | Dominio completo: usuarios, predios, equipamentos, checklist, servicos, calendario, relatorios e APIs. |

Nao existem outros apps Django locais alem de `core`.

## Dependencias instaladas

Dependencias do ambiente virtual do backend, obtidas com `venv/bin/python -m pip freeze`:

| Pacote | Versao | Uso provavel |
| --- | ---: | --- |
| `asgiref` | `3.11.1` | Dependencia Django/ASGI. |
| `Django` | `6.0.3` | Framework web principal. |
| `djangorestframework` | `3.17.1` | API DRF e token auth. |
| `pillow` | `12.1.1` | Suporte a `ImageField` e manipulacao de imagens. |
| `qrcode` | `8.2` | Geracao de QR codes de equipamentos. |
| `sqlparse` | `0.5.5` | Dependencia Django para SQL parsing. |

Ambiente Python:

- `Python 3.14.3`.

Dependencias mobile observadas em `mobile/package.json`:

- `expo ~54.0.33`
- `react 19.1.0`
- `react-native 0.81.5`
- `axios ^1.15.0`
- `@react-native-async-storage/async-storage 2.2.0`
- `@react-navigation/native ^7.2.2`
- `@react-navigation/native-stack ^7.14.11`
- `expo-camera`, `expo-image-picker`, `expo-status-bar`

## Estado de migrations, testes e dados locais

Migrations aplicadas:

- Todas as migrations de `admin`, `auth`, `authtoken`, `contenttypes`, `sessions` e `core` aparecem aplicadas.
- `core` tem migrations `0001` a `0011`.
- `0010_relatoriogerado.py` e `0011_relatoriogerado_equipamento.py` foram geradas manualmente.

Testes:

- `venv/bin/python manage.py check`: passou, sem issues.
- `venv/bin/python manage.py test`: 4 testes passaram.

Cobertura atual:

- Os testes existentes cobrem permissao basica de usuario comum vs gestor para criar predio, criacao de servico por usuario comum e bloqueio de atualizacao de rascunho de outro usuario.
- Nao ha cobertura para API DRF mobile, QR code, upload de fotos, relatorios, calendario, migracao para PostgreSQL ou constraints de dados.

Dados locais do SQLite, por contagem:

| Modelo | Registros |
| --- | ---: |
| `Predio` | 1 |
| `Departamento` | 2 |
| `Grupo` | 2 |
| `TipoEquipamento` | 3 |
| `TipoServico` | 1 |
| `Periodicidade` | 1 |
| `Equipamento` | 1 |
| `Inspecao` | 0 |
| `ServicoTipoEquipamento` | 1 |
| `SecaoChecklist` | 1 |
| `ItemChecklist` | 2 |
| `Servico` | 7 |
| `RespostaChecklist` | 5 |
| `AcaoCorretiva` | 0 |
| `UsuarioPerfil` | 3 |
| `RelatorioGerado` | 8 |

Qualidade basica observada no SQLite:

- Equipamentos sem `numero_serie`: 0.
- Equipamentos sem `tipo_equipamento`: 0.
- Equipamentos sem `predio`: 0.
- `ServicoTipoEquipamento` sem `periodicidade`: 0.
- `SecaoChecklist` sem `servico_tipo_equipamento`: 0.
- `ItemChecklist` sem `secao`: 0.

## Models e relacionamentos

Todos os models locais estao em `core.models`.

### `Predio`

Representa locais ou sites fisicos.

Campos principais:

- `nome`, unico.
- `descricao`, `endereco`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos reversos:

- `departamentos`: departamentos do predio.
- `equipamentos`: equipamentos alocados no predio.
- `usuarios`: perfis de usuarios vinculados ao predio.

Regras auxiliares:

- `get_quantidade_departamentos()` conta departamentos ativos.

### `Departamento`

Representa setores/departamentos.

Campos principais:

- `nome`, unico.
- `descricao`, `localizacao`, `responsavel`, `email`, `telefone`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos:

- `predio -> Predio`, `ForeignKey`, `SET_NULL`, opcional, `related_name='departamentos'`.

Relacionamentos reversos:

- `equipamentos`: equipamentos vinculados ao departamento.
- `usuarios`: perfis de usuarios vinculados ao departamento.

### `Grupo`

Agrupa tipos/equipamentos.

Campos principais:

- `nome`, unico.
- `descricao`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos reversos:

- `tipos_equipamento`: tipos de equipamento deste grupo.
- `equipamentos`: equipamentos deste grupo.

Regras auxiliares:

- `get_quantidade_equipamentos()` conta equipamentos ativos do grupo.

### `Periodicidade`

Define frequencia de servicos e inspecoes.

Campos principais:

- `nome`, unico.
- `por_demanda`.
- `valor`.
- `tipo`: `dias`, `semanas`, `meses`, `anos`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos reversos:

- `tipos_equipamento`: tipos de equipamento que usam a periodicidade padrao.
- `servicos_configurados`: configuracoes de servicos que usam a periodicidade.
- `inspecoes`: inspecoes vinculadas.

Regras auxiliares:

- `get_descricao_completa()`.
- `get_rotulo_inspecao()`.

### `TipoEquipamento`

Representa categorias como extintor, mangueira, sirene etc.

Campos principais:

- `nome`, unico.
- `descricao`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos:

- `grupo -> Grupo`, `ForeignKey`, `CASCADE`, obrigatorio, `related_name='tipos_equipamento'`.
- `periodicidade -> Periodicidade`, `ForeignKey`, `SET_NULL`, opcional, `related_name='tipos_equipamento'`.

Relacionamentos reversos:

- `equipamentos`: equipamentos deste tipo.
- `servicos_configurados`: servicos configurados para este tipo.

Regras auxiliares:

- `get_checklist_count()` conta itens ativos de checklist por servicos configurados.

### `TipoServico`

Representa tipos de servico executaveis.

Campos principais:

- `nome`, unico.
- `descricao`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos reversos:

- `equipamentos_configurados`: configuracoes `ServicoTipoEquipamento`.
- `servicos`: servicos realizados.

### `ServicoTipoEquipamento`

Modelo de configuracao: define quais servicos existem para cada tipo de equipamento.

Campos principais:

- `obrigatorio`.
- `vencimento_final_mes`.
- `habilitar_assinatura`.
- `assinatura_obrigatoria`.
- `acoes_obrigatorias`.
- `permitir_servicos_massa`.
- `ordem`.
- `ativo`.
- `criado_em`.

Relacionamentos:

- `tipo_equipamento -> TipoEquipamento`, `ForeignKey`, `CASCADE`, `related_name='servicos_configurados'`.
- `tipo_servico -> TipoServico`, `ForeignKey`, `CASCADE`, `related_name='equipamentos_configurados'`.
- `periodicidade -> Periodicidade`, `ForeignKey`, `SET_NULL`, opcional no banco, `related_name='servicos_configurados'`.

Constraints:

- `unique_together = ['tipo_equipamento', 'tipo_servico', 'periodicidade']`.

Relacionamentos reversos:

- `secoes_checklist`: secoes vinculadas a esta configuracao.

Observacao:

- Como `periodicidade` pode ser `NULL`, a unicidade para combinacoes sem periodicidade pode nao impedir duplicatas em bancos SQL tradicionais. PostgreSQL permite multiplos `NULL` em unique constraints.

### `SecaoChecklist`

Agrupa itens de checklist dentro de um servico configurado.

Campos principais:

- `nome`.
- `descricao`.
- `ordem`.
- `ativo`.
- `criado_em`.

Relacionamentos:

- `servico_tipo_equipamento -> ServicoTipoEquipamento`, `ForeignKey`, `CASCADE`, opcional, `related_name='secoes_checklist'`.

Relacionamentos reversos:

- `itens`: itens de checklist.

Observacao:

- Migrations antigas ja tiveram `tipo_equipamento` direto em `SecaoChecklist`, mas o campo foi removido em `0007`. Ainda existe codigo legado em `views.py` que tenta usar esse campo, mas essas views nao estao roteadas em `core.urls`.

### `ItemChecklist`

Pergunta ou item respondido durante um servico.

Campos principais:

- `pergunta`.
- `tipo_resposta`: `sim_nao`, `texto`, `numero`, `data`, `foto`.
- `ordem`.
- `obrigatorio`.
- `detalhamento`.
- `imagem_descritiva`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos:

- `secao -> SecaoChecklist`, `ForeignKey`, `CASCADE`, opcional, `related_name='itens'`.

Relacionamentos reversos:

- `respostas`: respostas em servicos.
- `acoes`: acoes corretivas ligadas ao item.

### `Equipamento`

Representa o ativo/equipamento fisico a ser inspecionado.

Campos principais:

- `nome`.
- `numero_serie`, unico, opcional.
- `marca`.
- `data_fabricacao`.
- `local`.
- `ponto_referencia`.
- `descricao`.
- `observacoes`.
- `foto`.
- `qr_code`.
- `ativo`.
- `criado_em`, `atualizado_em`.

Relacionamentos:

- `tipo_equipamento -> TipoEquipamento`, `ForeignKey`, `SET_NULL`, opcional, `related_name='equipamentos'`.
- `grupo -> Grupo`, `ForeignKey`, `SET_NULL`, opcional, `related_name='equipamentos'`.
- `predio -> Predio`, `ForeignKey`, `SET_NULL`, opcional, `related_name='equipamentos'`.
- `departamento -> Departamento`, `ForeignKey`, `SET_NULL`, opcional, `related_name='equipamentos'`.

Campos obsoletos:

- `numero_extintor`.
- `numero_cilindro`.

Regras no `save()`:

- Se `tipo_equipamento` foi selecionado e `grupo` esta vazio, preenche `grupo` a partir do tipo.
- Se nao ha `qr_code`, gera imagem de QR code com conteudo hardcoded: `http://127.0.0.1:8000/equipamentos/{id}/`.

Relacionamentos reversos:

- `inspecoes`.
- `servicos`.

### `Inspecao`

Modelo de inspecao planejada ou historica.

Campos principais:

- `nome_inspecao`.
- `data_vencimento`.
- `data_realizada`.
- `status`: `pendente`, `realizada`, `atrasada`, `cancelada`.
- `observacoes`.
- `criado_em`, `atualizado_em`.

Relacionamentos:

- `equipamento -> Equipamento`, `ForeignKey`, `CASCADE`, `related_name='inspecoes'`.
- `periodicidade -> Periodicidade`, `ForeignKey`, `SET_NULL`, `related_name='inspecoes'`.

Observacao:

- O calendario atual calcula previsoes a partir de `ServicoTipoEquipamento` e `Servico`; `Inspecao` parece pouco usado ou legado.

### `UsuarioPerfil`

Perfil complementar ao `django.contrib.auth.models.User`.

Campos principais:

- `tipo_acesso`: `admin`, `analista`, `usuario`, `convidado`.
- `sites`: `C3`, `C4`, `C5`, `todos`.
- `filtros`.
- `status`: `ativo`, `inativo`, `pendente`.
- `observacoes`.
- `ultimo_acesso`.
- `foto`.
- `data_criacao`, `data_atualizacao`.

Relacionamentos:

- `user -> User`, `OneToOneField`, `CASCADE`, `related_name='perfil'`.
- `departamento -> Departamento`, `ForeignKey`, `SET_NULL`, opcional, `related_name='usuarios'`.
- `predio -> Predio`, `ForeignKey`, `SET_NULL`, opcional, `related_name='usuarios'`.

Regras auxiliares:

- `get_nome_completo()`.
- `is_admin()`.
- `is_analista()`.
- `is_ativo()`.

Observacao:

- Nao ha signal para criar perfil automaticamente para todo usuario. Algumas views usam `get_or_create`.

### `Servico`

Representa um servico/checklist executado ou um rascunho.

Campos principais:

- `data_realizacao`, `auto_now_add`.
- `observacoes`.
- `status`: `rascunho`, `concluido`, `cancelado`.
- `pontuacao_total`.
- `pontuacao_maxima`.
- `criado_em`, `atualizado_em`.

Relacionamentos:

- `equipamento -> Equipamento`, `ForeignKey`, `CASCADE`, `related_name='servicos'`.
- `tipo_servico -> TipoServico`, `ForeignKey`, `SET_NULL`, opcional, `related_name='servicos'`.
- `realizado_por -> User`, `ForeignKey`, `SET_NULL`, opcional, `related_name='servicos_realizados'`.

Relacionamentos reversos:

- `respostas`.
- `acoes_corretivas`.

Regras auxiliares:

- `calcular_pontuacao_percentual()`.

Observacao:

- Existem dois timestamps de criacao (`data_realizacao` e `criado_em`) com semantica muito parecida.

### `RespostaChecklist`

Resposta dada a um item dentro de um servico.

Campos principais:

- `opcao`: `atende`, `nao_atende`, `nao_aplica`.
- `observacao`.
- `fotos`.
- `criado_em`.

Relacionamentos:

- `servico -> Servico`, `ForeignKey`, `CASCADE`, `related_name='respostas'`.
- `item_checklist -> ItemChecklist`, `ForeignKey`, `CASCADE`, `related_name='respostas'`.

### `AcaoCorretiva`

Acao corretiva gerada a partir de um item nao conforme.

Campos principais:

- `problema`.
- `acao`.
- `responsaveis`.
- `prazo`.
- `anexos`.
- `criado_em`.

Relacionamentos:

- `servico -> Servico`, `ForeignKey`, `CASCADE`, `related_name='acoes_corretivas'`.
- `item_checklist -> ItemChecklist`, `ForeignKey`, `CASCADE`, `related_name='acoes'`.

Observacao:

- A view de criacao aceita `servico_id` ausente, mas o model exige `servico`. Isso pode gerar erro de integridade.

### `RelatorioGerado`

Historico de relatorios exportados.

Campos principais:

- `tipo`, atualmente apenas `condensado`.
- `data_inicio`, `data_fim`.
- `total_servicos`.
- `total_equipamentos`.
- `total_nao_conformes`.
- `media_pontuacao`.
- `arquivo_nome`.
- `criado_em`.

Relacionamentos:

- `predio -> Predio`, `ForeignKey`, `SET_NULL`, opcional.
- `tipo_equipamento -> TipoEquipamento`, `ForeignKey`, `SET_NULL`, opcional.
- `tipo_servico -> TipoServico`, `ForeignKey`, `SET_NULL`, opcional.
- `equipamento -> Equipamento`, `ForeignKey`, `SET_NULL`, opcional.
- `criado_por -> User`, `ForeignKey`, `SET_NULL`, opcional, `related_name='relatorios_gerados'`.

## Mapa resumido de relacionamentos

```text
User 1--1 UsuarioPerfil
User 1--N Servico
User 1--N RelatorioGerado

Predio 1--N Departamento
Predio 1--N Equipamento
Predio 1--N UsuarioPerfil

Departamento 1--N Equipamento
Departamento 1--N UsuarioPerfil

Grupo 1--N TipoEquipamento
Grupo 1--N Equipamento

Periodicidade 1--N TipoEquipamento
Periodicidade 1--N ServicoTipoEquipamento
Periodicidade 1--N Inspecao

TipoEquipamento 1--N Equipamento
TipoEquipamento 1--N ServicoTipoEquipamento

TipoServico 1--N ServicoTipoEquipamento
TipoServico 1--N Servico

ServicoTipoEquipamento 1--N SecaoChecklist
SecaoChecklist 1--N ItemChecklist

Equipamento 1--N Inspecao
Equipamento 1--N Servico

Servico 1--N RespostaChecklist
Servico 1--N AcaoCorretiva

ItemChecklist 1--N RespostaChecklist
ItemChecklist 1--N AcaoCorretiva
```

## Admin Django

Registrados em `core/admin.py`:

- `Equipamento`
- `Grupo`
- `Departamento`
- `Predio`
- `TipoEquipamento`
- `TipoServico`
- `Periodicidade`
- `UsuarioPerfil`

Nao registrados no admin:

- `Inspecao`
- `ServicoTipoEquipamento`
- `SecaoChecklist`
- `ItemChecklist`
- `Servico`
- `RespostaChecklist`
- `AcaoCorretiva`
- `RelatorioGerado`

Isso dificulta manutencao operacional e depuracao pelo admin, especialmente para servicos, respostas, acoes corretivas e historico de relatorios.

## URLs e views existentes

### URLconf principal

Arquivo: `backend/notchfire_project/urls.py`

| Rota | Destino |
| --- | --- |
| `/admin/` | Admin Django. |
| `/` | Inclui `core.urls`. |
| `/api/` | Inclui `core.urls_api`. |
| `/media/...` | Servido em `DEBUG=True`. |

Ordem relevante:

1. `core.urls` e incluido na raiz primeiro.
2. `core.urls_api` e incluido depois em `/api/`.

Por causa dessa ordem, rotas internas de `core.urls` que comecam com `api/` tem prioridade sobre rotas DRF de `core.urls_api`.

### Rotas HTML e JSON internas em `core.urls`

Arquivo: `backend/core/urls.py`

#### Autenticacao e paginas principais

| Rota | View | Observacao |
| --- | --- | --- |
| `/` | `index` | Redireciona para login. |
| `/login/` | `login_view` | Login por sessao. |
| `/logout/` | `logout_view` | Logout por sessao. |
| `/home/` | `home_view` | Pagina inicial autenticada. |
| `/minha_conta/` | `minha_conta_view` | Perfil e senha do usuario logado. |

#### Usuarios

| Rota | View | Observacao |
| --- | --- | --- |
| `/usuarios/` | `usuarios_view` | Tela web, apenas superuser. |
| `/criar_usuario/` | `criar_usuario_view` | Redireciona para usuarios, apenas superuser. |
| `/api/usuarios/` | `api_usuarios_listar` | Lista, filtros, paginacao. |
| `/api/usuarios/criar/` | `api_usuarios_criar` | Cria usuario e perfil. |
| `/api/usuarios/<id>/` | `api_usuarios_detalhe` | GET/POST/PUT/DELETE para usuario. |

#### Equipamentos

| Rota | View | Observacao |
| --- | --- | --- |
| `/equipamentos/` | `equipamentos_view` | Pagina web/listagem simples. |
| `/equipamentos/criar/` | `criar_equipamento_view` | Protegida por `gestor_required`. |
| `/equipamentos/<id>/` | `detalhe_equipamento_view` | Detalhe e historico. |
| `/equipamentos/<id>/editar/` | `editar_equipamento_view` | Protegida por `gestor_required`. |
| `/api/equipamentos/` | `api_equipamentos_listar` | Lista JSON para web. Sombreia o DRF ViewSet de equipamentos. |
| `/api/equipamentos-para-servico/` | `api_equipamentos_para_servico` | Lista equipamentos ativos para criar servico. |
| `/api/equipamentos/<id>/` | `api_equipamento_detalhes` | Detalhes JSON. Sombreia o detail do DRF ViewSet. |
| `/api/equipamentos/<id>/editar/` | `api_equipamento_editar_detalhe` | Protegida por `gestor_required`. |
| `/api/equipamentos/<id>/toggle-ativo/` | `api_equipamento_toggle_ativo` | Protegida por `gestor_required`. |
| `/api/equipamentos/<id>/foto/` | `api_equipamento_upload_foto` | Protegida por `gestor_required`. |
| `/api/equipamentos/<id>/excluir/` | `api_equipamento_excluir` | Protegida por `gestor_required`. |

#### Predios, departamentos e grupos

| Rota | View | Observacao |
| --- | --- | --- |
| `/predios/` | `predios_view` | Tela web. |
| `/api/predios/` | `api_predios_listar` | Lista/filtros/paginacao. |
| `/api/predios/criar/` | `api_predios_criar` | Protegida por `gestor_required`. |
| `/api/predios/<id>/editar/` | `api_predios_editar` | Protegida por `gestor_required`. |
| `/api/predios/<id>/excluir/` | `api_predios_excluir` | Protegida por `gestor_required`. |
| `/api/predios-para-select/` | `api_predios_para_select` | Dados para selects. |
| `/departamentos/` | `departamentos_view` | Tela web. |
| `/api/departamentos/` | `api_departamentos_listar` | Lista/filtros/paginacao. |
| `/api/departamentos/criar/` | `api_departamentos_criar` | Protegida por `gestor_required`. |
| `/api/departamentos/<id>/editar/` | `api_departamentos_editar` | Protegida por `gestor_required`. |
| `/api/departamentos/<id>/excluir/` | `api_departamentos_excluir` | Protegida por `gestor_required`. |
| `/api/departamentos-por-predio/` | `api_departamentos_por_predio` | Filtra departamentos por predio. |
| `/api/departamentos-para-select/` | `api_departamentos_para_select` | Dados para selects. |
| `/grupos/` | `grupos_view` | Tela web. |
| `/api/grupos/` | `api_grupos_listar` | Lista/filtros/paginacao. |
| `/api/grupos/criar/` | `api_grupos_criar` | Protegida por `gestor_required`. |
| `/api/grupos/<id>/editar/` | `api_grupos_editar` | Protegida por `gestor_required`. |
| `/api/grupos/<id>/excluir/` | `api_grupos_excluir` | Protegida por `gestor_required`. |
| `/api/grupos-para-select/` | `api_grupos_listar_para_select` | Dados para selects. |

#### Tipos de servico e periodicidades

| Rota | View | Observacao |
| --- | --- | --- |
| `/tipos-servico/` | `tipos_servico_view` | Tela web. |
| `/api/tipos-servico/` | `api_tipos_servico_listar` | Lista/filtros/paginacao. |
| `/api/tipos-servico/criar/` | `api_tipos_servico_criar` | Protegida por `gestor_required`. |
| `/api/tipos-servico/<id>/editar/` | `api_tipos_servico_editar` | Protegida por `gestor_required`. |
| `/api/tipos-servico/<id>/excluir/` | `api_tipos_servico_excluir` | Protegida por `gestor_required`. |
| `/periodicidades/` | `periodicidades_view` | Tela web. |
| `/api/periodicidades/` | `api_periodicidades_listar` | Lista/filtros/paginacao. |
| `/api/periodicidades/criar/` | `api_periodicidades_criar` | Protegida por `gestor_required`. |
| `/api/periodicidades/<id>/editar/` | `api_periodicidades_editar` | Protegida por `gestor_required`. |
| `/api/periodicidades/<id>/excluir/` | `api_periodicidades_excluir` | Protegida por `gestor_required`. |
| `/api/periodicidades-para-select/` | `api_periodicidades_para_select` | Dados para selects. |

#### Tipos de equipamento, configuracao de servicos e checklist

| Rota | View | Observacao |
| --- | --- | --- |
| `/tipos-equipamento/` | `tipos_equipamento_view` | Tela web. |
| `/tipos-equipamento/<id>/` | `detalhe_tipo_equipamento_view` | Editor principal, protegido por `gestor_required`. |
| `/api/tipos-equipamento/` | `api_tipos_equipamento_listar` | Lista/filtros/paginacao. |
| `/api/tipos-equipamento/criar/` | `api_tipos_equipamento_criar` | Protegida por `gestor_required`. |
| `/api/tipos-equipamento/<id>/editar/` | `api_tipos_equipamento_editar` | Protegida por `gestor_required`. |
| `/api/tipos-equipamento/<id>/excluir/` | `api_tipos_equipamento_excluir` | Protegida por `gestor_required`. |
| `/api/tipos-equipamento/<id>/info/` | `api_tipo_equipamento_info` | Atualiza dados basicos no editor. |
| `/api/tipo-equipamento-detalhe/` | `api_tipo_equipamento_detalhe` | Retorna periodicidade e data sugerida. |
| `/api/tipos-equipamento/servicos/criar/` | `api_editor_servico_criar` | Cria configuracao de servico. |
| `/api/tipos-equipamento/servicos/<id>/` | `api_editor_servico_detalhes` | Detalhe de configuracao. |
| `/api/tipos-equipamento/servicos/<id>/editar/` | `api_editor_servico_editar` | Protegida por `gestor_required`. |
| `/api/tipos-equipamento/servicos/<id>/excluir/` | `api_editor_servico_excluir` | Protegida por `gestor_required`. |
| `/api/tipos-equipamento/servicos/<id>/checklist/apagar/` | `api_editor_checklist_apagar` | Remove todas as secoes do servico. |
| `/api/secoes-checklist/criar/` | `api_editor_secao_criar` | Cria secao. |
| `/api/secoes-checklist/<id>/editar/` | `api_editor_secao_editar` | Edita secao. |
| `/api/secoes-checklist/<id>/excluir/` | `api_editor_secao_excluir` | Remove secao. |
| `/api/itens-checklist/criar/` | `api_editor_item_criar` | Cria item simples via JSON. |
| `/api/itens-checklist/<id>/editar/` | `api_editor_item_editar` | Edita item simples via JSON. |
| `/api/itens-checklist/<id>/excluir/` | `api_editor_item_excluir` | Remove item. |
| `/api/checklist-itens/criar/` | `api_checklist_item_criar` | Cria item via multipart, com imagem. |
| `/api/checklist-itens/<id>/` | `api_checklist_item_detalhes` | Detalhe de item. |
| `/api/checklist-itens/<id>/editar/` | `api_checklist_item_editar` | Edita item via multipart. |
| `/api/checklist-itens/<id>/excluir/` | `api_checklist_item_excluir` | Remove item. |
| `/tipos-equipamento/<tipo_id>/servicos/criar/` | `criar_servico_tipo_equipamento_view` | POST HTML. |
| `/servicos-tipo-equipamento/<id>/editar/` | `editar_servico_tipo_equipamento_view` | POST HTML. |
| `/servicos-tipo-equipamento/<id>/excluir/` | `excluir_servico_tipo_equipamento_view` | POST HTML. |
| `/servicos-tipo-equipamento/<servico_id>/secoes/criar/` | `criar_secao_checklist_view` | POST HTML. |
| `/secoes-checklist/<id>/editar/` | `editar_secao_checklist_view` | POST HTML. |
| `/secoes-checklist/<id>/excluir/` | `excluir_secao_checklist_view` | POST HTML. |
| `/servicos-tipo-equipamento/<servico_id>/itens/criar/` | `criar_item_checklist_view` | POST HTML. |
| `/itens-checklist/<id>/editar/` | `editar_item_checklist_view` | POST HTML. |
| `/itens-checklist/<id>/excluir/` | `excluir_item_checklist_view` | POST HTML. |

#### Servicos, rascunhos, calendario e relatorios

| Rota | View | Observacao |
| --- | --- | --- |
| `/servicos/` | `servicos_view` | Tela web de servicos. |
| `/rascunho/` | `rascunhos_view` | Alias singular. |
| `/rascunhos/` | `rascunhos_view` | Tela web de rascunhos. |
| `/calendario/` | `calendario_view` | Tela web de calendario. |
| `/relatorios/` | `relatorios_view` | Tela web de relatorios. |
| `/api/calendario/filtros/` | `api_calendario_filtros` | Opcoes de filtros. |
| `/api/calendario/eventos/` | `api_calendario_eventos` | Eventos previstos, vencidos e realizados. |
| `/calendario/exportar/` | `exportar_calendario_dados` | Exporta CSV. |
| `/api/servicos/` | `api_servicos_listar` | Lista/filtros/paginacao. |
| `/api/servicos/criar/` | `api_servicos_criar` | Cria servico ou rascunho web. Sombreia rota DRF `/api/servicos/criar/`. |
| `/api/servicos/<id>/` | `api_servicos_detalhes` | Detalhe de servico. |
| `/api/servicos/<id>/atualizar/` | `api_servicos_atualizar` | Atualiza rascunho/servico conforme permissao. |
| `/api/servicos/rascunho/` | `api_servicos_rascunho` | Verifica rascunho existente. |
| `/api/servicos/<id>/descartar/` | `api_servicos_descartar` | Descarta rascunho proprio. |
| `/api/rascunhos/` | `api_rascunhos_listar` | Lista rascunhos do usuario. |
| `/api/tipos-servico-para-equipamento/` | `api_tipos_servico_para_equipamento` | Lista servicos configurados. |
| `/api/checklist-itens-por-tipo/` | `api_checklist_itens_por_tipo` | Itens por tipo de equipamento e tipo de servico. |
| `/api/acoes-corretivas/criar/` | `api_acoes_corretivas_criar` | Cria acao corretiva, protegida por `gestor_required`. |
| `/api/relatorios/filtros/` | `api_relatorios_filtros` | Opcoes de filtros. |
| `/api/relatorios/resumo/` | `api_relatorios_resumo` | Metricas resumidas. |
| `/api/relatorios/historico/` | `api_relatorios_historico` | Historico do usuario. |
| `/relatorios/exportar/condensado/` | `exportar_relatorio_condensado` | Gera PDF e registra historico. |
| `/relatorios/<id>/baixar/` | `baixar_relatorio_gerado` | Recria e baixa PDF historico. |

### Rotas DRF em `core.urls_api`

Arquivo: `backend/core/urls_api.py`

Todas sao montadas sob `/api/` pelo URLconf principal.

| Rota final | View/API | Observacao |
| --- | --- | --- |
| `/api/login/` | `LoginAPI` | Retorna token e dados do usuario. |
| `/api/dashboard/` | `DashboardAPI` | Retorna indicadores, tarefas e ultimas inspecoes. |
| `/api/me/` | `PerfilAPI` | Perfil do usuario autenticado. |
| `/api/mobile/servicos/criar/` | `ServicoCriarAPI` | Criacao de servico/checklist para mobile. |
| `/api/mobile/checklist-itens/` | `ChecklistItensAPI` | Itens de checklist para mobile. |
| `/api/mobile/equipamentos/<id>/tipos-servico/` | `EquipamentoTiposServicoAPI` | Tipos de servico para equipamento. |
| `/api/mobile/qr/equipamento/` | `QRCodeEquipamentoAPI` | Resolve QR code para equipamento. |
| `/api/servicos/criar/` | `ServicoCriarAPI` | Duplicada/sombreada por `core.urls`. |
| `/api/checklist-itens/` | `ChecklistItensAPI` | Endpoint DRF sem conflito exato com core. |
| `/api/equipamentos/<id>/tipos-servico/` | `EquipamentoTiposServicoAPI` | Sem conflito exato com core. |
| `/api/qr/equipamento/` | `QRCodeEquipamentoAPI` | Sem conflito com core. |
| `/api/equipamentos/` | `EquipamentoViewSet` via router | Sombreada por `api_equipamentos_listar` de `core.urls`. |
| `/api/equipamentos/<pk>/` | `EquipamentoViewSet` via router | Sombreada por `api_equipamento_detalhes` de `core.urls`. |

Classes DRF:

- `LoginAPI`: herda de `ObtainAuthToken`.
- `PerfilAPI`: `APIView`, `IsAuthenticated`.
- `QRCodeEquipamentoAPI`: `APIView`, `IsAuthenticated`.
- `EquipamentoTiposServicoAPI`: `APIView`, `IsAuthenticated`.
- `ChecklistItensAPI`: `APIView`, `IsAuthenticated`.
- `ServicoCriarAPI`: `APIView`, `IsAuthenticated`.
- `EquipamentoViewSet`: `ModelViewSet`, `IsAuthenticated` e `IsGestorForWrites`.
- `DashboardAPI`: `APIView`, `IsAuthenticated`.

### Views definidas mas aparentemente nao roteadas

No final de `core/views.py` existem views do "editor de tipo de equipamento" que nao aparecem em `core.urls.py`:

- `editor_tipo_equipamento_view`
- `api_tipo_equipamento_servico_criar`
- `api_tipo_equipamento_servico_detalhes`
- `api_tipo_equipamento_servico_editar`
- `api_tipo_equipamento_servico_excluir`
- `api_tipo_equipamento_secao_criar`
- `api_tipo_equipamento_secao_detalhes`
- `api_tipo_equipamento_secao_editar`
- `api_tipo_equipamento_secao_excluir`
- `api_tipo_equipamento_item_criar`
- `api_tipo_equipamento_item_detalhes`
- `api_tipo_equipamento_item_editar`
- `api_tipo_equipamento_item_excluir`

Essas views parecem legadas porque referenciam campos removidos ou inexistentes:

- `SecaoChecklist.objects.filter(tipo_equipamento=...)`, mas `SecaoChecklist` nao possui mais `tipo_equipamento`.
- `ServicoTipoEquipamento.site`, mas `ServicoTipoEquipamento` nao possui campo `site`.

Tambem existe codigo duplicado/inacessivel em `api_acoes_corretivas_criar`: ha um segundo bloco `except Exception` apos outro `except Exception`, sintaticamente valido, mas logicamente morto.

## Fluxos principais

### Cadastro e manutencao de equipamentos

1. Gestor cria ou edita equipamento por tela HTML ou endpoints internos.
2. `Equipamento.save()` preenche `grupo` se houver `tipo_equipamento`.
3. `Equipamento.save()` gera QR code se o campo `qr_code` estiver vazio.
4. O QR code aponta para URL local `http://127.0.0.1:8000/equipamentos/{id}/`.

### Configuracao de checklist

1. Gestor cadastra grupos, periodicidades, tipos de servico e tipos de equipamento.
2. Para cada `TipoEquipamento`, cria `ServicoTipoEquipamento`.
3. Para cada servico configurado, cria `SecaoChecklist`.
4. Para cada secao, cria `ItemChecklist`.

### Execucao de servico/checklist pela web

1. Usuario abre `/servicos/`.
2. Frontend chama `/api/equipamentos-para-servico/`.
3. Ao escolher equipamento, chama `/api/tipos-servico-para-equipamento/`.
4. Ao escolher servico, chama `/api/checklist-itens-por-tipo/`.
5. Cria ou atualiza servico por `/api/servicos/criar/` ou `/api/servicos/<id>/atualizar/`.
6. Respostas sao gravadas em `RespostaChecklist`.
7. Pontuacao e recalculada na view.

### Execucao de servico/checklist pelo mobile

1. Mobile autentica em `/api/login/` e guarda `Token` em `AsyncStorage`.
2. Scanner ou entrada manual chama `/api/mobile/qr/equipamento/`.
3. Mobile carrega itens em `/api/mobile/checklist-itens/`.
4. Mobile envia resultado para `/api/mobile/servicos/criar/`.

Risco atual:

- O mobile envia `respostas` como JSON string dentro de `FormData`, mas `ServicoCriarAPI` espera lista Python/JSON em `request.data`. Isso tende a quebrar em multipart ou ignorar fotos.
- A API mobile nao salva fotos nas respostas, apesar de o app montar campos `foto_<item_id>`.

### Calendario

O calendario nao depende diretamente do model `Inspecao`. Ele calcula eventos a partir de:

- Equipamentos ativos.
- Configuracoes `ServicoTipoEquipamento` com periodicidade.
- Servicos concluidos.
- Ultimo servico concluido por equipamento/tipo de servico.

Endpoints principais:

- `/api/calendario/filtros/`.
- `/api/calendario/eventos/`.
- `/calendario/exportar/`.

### Relatorios

Relatorios usam `Servico`, `RespostaChecklist` e `AcaoCorretiva`.

O PDF e gerado manualmente em `views.py`, sem biblioteca externa de PDF, por montagem direta de bytes PDF.

Endpoints principais:

- `/api/relatorios/filtros/`.
- `/api/relatorios/resumo/`.
- `/relatorios/exportar/condensado/`.
- `/api/relatorios/historico/`.
- `/relatorios/<id>/baixar/`.

## Pontos que podem dificultar a migracao para PostgreSQL

### 1. Configuracao de banco fixa em SQLite

`DATABASES` esta hardcoded para:

```python
'ENGINE': 'django.db.backends.sqlite3'
'NAME': BASE_DIR / 'db.sqlite3'
```

Nao ha suporte por variaveis de ambiente, `DATABASE_URL`, settings por ambiente ou dependencia `psycopg`/`psycopg2`.

Impacto:

- A migracao exige alterar settings e instalar driver PostgreSQL.
- Testes e desenvolvimento ainda validam so SQLite.

### 2. Ausencia de arquivo formal de dependencias

Nao existe `requirements.txt` ou `pyproject.toml`.

Impacto:

- Reproduzir o ambiente em servidor/CI fica fragil.
- A inclusao do driver PostgreSQL pode ficar manual e nao rastreada.

### 3. Constraints com campos nullable

`ServicoTipoEquipamento` usa:

```python
unique_together = ['tipo_equipamento', 'tipo_servico', 'periodicidade']
```

Como `periodicidade` pode ser `NULL`, PostgreSQL permite multiplas linhas com a mesma combinacao quando `periodicidade` for nula.

Impacto:

- Se a regra de negocio espera unicidade mesmo sem periodicidade, a constraint atual nao garante isso.
- Seria melhor usar `UniqueConstraint` com condicao, ou normalizar para periodicidade obrigatoria.

### 4. Unicidade e normalizacao de texto

Campos como `nome` sao `unique=True`, mas a normalizacao para uppercase/strip acontece em forms e views, nao no banco.

Exemplos:

- `Grupo.nome`
- `Departamento.nome`
- `Predio.nome`
- `TipoEquipamento.nome`
- `TipoServico.nome`
- `Periodicidade.nome`

Impacto:

- Duplicatas por case/espaco podem passar se dados entrarem por outro caminho.
- PostgreSQL mantem comparacao case-sensitive por padrao. Se a regra desejada for case-insensitive, considerar `UniqueConstraint(Lower(...))` ou `CITEXT`.

### 5. Campos legados e historico de schema

`Equipamento` ainda mantem:

- `numero_extintor`
- `numero_cilindro`

`Inspecao` existe, mas o calendario atual parece usar `Servico` e `ServicoTipoEquipamento`.

Impacto:

- Dados legados podem ficar ambiguos na migracao.
- Antes de migrar, convem decidir se esses campos continuam como compatibilidade, se serao removidos ou se precisam de data migration.

### 6. Codigo legado referenciando campos removidos

Views nao roteadas no final de `core/views.py` referenciam campos removidos:

- `SecaoChecklist.tipo_equipamento`.
- `ServicoTipoEquipamento.site`.

Impacto:

- Nao impede a migracao se as views continuarem nao roteadas.
- Mas pode quebrar se alguem reativar essas rotas durante refatoracao ou migracao.

### 7. Muitos relacionamentos opcionais

Ha varios FKs `SET_NULL`, `null=True`, `blank=True`:

- `Equipamento.tipo_equipamento`, `grupo`, `predio`, `departamento`.
- `SecaoChecklist.servico_tipo_equipamento`.
- `ItemChecklist.secao`.
- `Servico.tipo_servico`, `realizado_por`.
- Filtros de `RelatorioGerado`.

Impacto:

- PostgreSQL nao aceita inconsistencias, mas aceita nulls. O risco e de logica quebrar em consultas que assumem relacao obrigatoria.
- Atualmente o banco local nao apresentou nulos nos vinculos principais, mas isso deve ser validado antes de migrar dados reais.

### 8. Indices insuficientes para volume maior

O sistema filtra frequentemente por:

- `ativo`.
- `criado_em`.
- `status`.
- `equipamento_id`.
- `tipo_servico_id`.
- `tipo_equipamento_id`.
- `predio_id`.
- `departamento_id`.
- `realizado_por_id`.
- `respostas__opcao`.

Impacto:

- PostgreSQL funcionara, mas consultas de calendario, dashboard e relatorios podem degradar com volume.
- Recomendavel adicionar indices compostos conforme queries reais.

### 9. Uso intensivo de `__date` em DateTimeField

Exemplos:

- `criado_em__date__gte`
- `criado_em__date__lte`

Impacto:

- Em PostgreSQL, casts de timestamp para date podem prejudicar uso de indice.
- Com `TIME_ZONE='UTC'`, datas exibidas/filtradas em contexto brasileiro podem divergir da expectativa do usuario se nao houver conversao consistente.

### 10. Geracao de QR code no `save()`

`Equipamento.save()` gera arquivo e salva novamente o model.

Impacto:

- Ao importar dados para PostgreSQL, saves em massa podem gerar arquivos inesperados ou QR codes com URL local.
- Melhor separar geracao de QR em service/command explicito e usar uma configuracao `SITE_URL`.

### 11. Media local acoplada ao projeto

Arquivos de `ImageField` e `FileField` estao em `backend/media/`.

Impacto:

- Migrar banco nao migra arquivos.
- E preciso plano separado para copiar media e preservar caminhos relativos.

### 12. Falta de validacao em transacoes

Criacao de servico cria `Servico`, depois varias `RespostaChecklist`, depois atualiza pontuacao.

Impacto:

- Em erro intermediario, pode sobrar servico parcial.
- PostgreSQL deixara mais claro erro de integridade, mas a aplicacao deveria usar `transaction.atomic()` nesses fluxos.

## Pontos que podem dificultar a criacao de uma API para o app mobile

### 1. Dois tipos de API dividem o mesmo prefixo `/api/`

O frontend web usa endpoints internos como:

- `/api/equipamentos/`
- `/api/servicos/criar/`
- `/api/tipos-equipamento/`

A API DRF mobile tambem fica em `/api/`.

Impacto:

- Rotas DRF ficam sombreadas por rotas internas por causa da ordem do URLconf.
- `/api/equipamentos/` no mobile nao chega ao `EquipamentoViewSet`; cai em `api_equipamentos_listar`, que usa `login_required` por sessao.
- `/api/servicos/criar/` DRF tambem e sombreada pela view interna.

Recomendacao:

- Separar namespaces, por exemplo:
  - `/web-api/` para endpoints AJAX de templates.
  - `/api/v1/` para API DRF mobile.

### 2. Contrato mobile de equipamentos esta desalinhado

`mobile/src/screens/EquipamentosScreen.tsx` chama:

```ts
api.get('equipamentos/')
```

Com `baseURL = http://127.0.0.1:8000/api/`, isso chama `/api/equipamentos/`.

Problemas:

- Essa rota e sombreada pela API web, nao pela DRF.
- A rota web exige sessao Django, nao token DRF.
- O tipo TypeScript da tela espera campos legados como `numero_extintor`, `tipo_equipamento`, `grupo`, `peso`, `foto`, `qr_code`.
- O `EquipamentoSerializer` DRF atual exporia `fields='__all__'`, com FKs como IDs e URLs de arquivo nao necessariamente absolutas.

### 3. Upload multipart de checklist mobile nao esta completo

O mobile envia:

- `equipamento_id`
- `tipo_servico_id`
- `observacoes`
- `status`
- `respostas` como JSON string
- arquivos `foto_<item_id>`

`ServicoCriarAPI` espera `respostas` como lista e nao faz `json.loads` quando recebe multipart.

Impacto:

- Em multipart, `respostas` tende a chegar como string.
- O loop `for resposta in respostas` pode iterar caracteres em vez de objetos.
- Fotos enviadas pelo mobile nao sao associadas a `RespostaChecklist.fotos`.

### 4. Sem versionamento de API

Nao existe `/api/v1/`, schema OpenAPI ou contratos versionados.

Impacto:

- Mudancas para atender web podem quebrar mobile.
- O app mobile fica sem contrato estavel.

### 5. Serializers insuficientes

Existe apenas:

- `EquipamentoSerializer` com `fields='__all__'`.

As demais respostas DRF sao montadas manualmente em dicts.

Impacto:

- Baixa consistencia de nomes, formatos de data, URLs absolutas e objetos relacionados.
- Dificulta documentar a API e criar testes de contrato.

### 6. Permissoes por perfil/site/predio nao sao aplicadas de forma consistente

`UsuarioPerfil` tem:

- `tipo_acesso`
- `sites`
- `filtros`
- `predio`
- `departamento`

Mas as queries de API nao aplicam consistentemente restricao por predio/site/departamento.

Impacto:

- Um usuario mobile autenticado pode enxergar dados globais dependendo do endpoint.
- Para uso em campo, provavelmente sera necessario escopo por predio/site/equipe.

### 7. Autenticacao por token simples

DRF usa `TokenAuthentication`.

Impacto:

- Nao ha expiracao, refresh token, revogacao por device ou rotacao.
- Token fica em `AsyncStorage`, que e simples de usar, mas nao e o armazenamento mais forte para credenciais sensiveis.

### 8. Base URL hardcoded no mobile

`mobile/src/services/api.ts`:

```ts
baseURL: 'http://127.0.0.1:8000/api/'
```

Impacto:

- App so funciona na rede local especifica.
- Ambientes dev/staging/prod exigem alteracao de codigo.

### 9. Dashboard e calendario podem ser pesados para mobile

`DashboardAPI` chama `_calendario_eventos_data`, que monta eventos do mes com equipamentos, configuracoes e servicos.

Impacto:

- Em bases maiores, a tela inicial mobile pode ficar lenta.
- Falta paginacao/limite explicito para algumas listas derivadas.

### 10. Respostas e erros sem padrao unico

Alguns endpoints retornam:

- `{'success': True, 'data': ...}`
- `{'success': True, 'itens': ...}`
- lista pura no DRF ViewSet.
- erros com `error`, `message` ou respostas HTML em caso de rota sombreada/login.

Impacto:

- O mobile precisa tratar muitos formatos.
- Aumenta risco de bugs silenciosos.

## Sugestoes de melhorias de arquitetura

### 1. Separar API web interna da API mobile

Proposta:

- Mover endpoints AJAX do template para `/web-api/`.
- Reservar `/api/v1/` para DRF.
- Manter redirects temporarios se necessario.

Beneficio:

- Remove sombreamento de rotas.
- Clarifica autenticacao: sessao web vs token mobile.

### 2. Criar apps por dominio

Hoje tudo fica em `core`. Uma divisao evolutiva possivel:

| App proposto | Conteudo |
| --- | --- |
| `accounts` | `UsuarioPerfil`, permissoes, perfil, autenticacao API. |
| `locations` | `Predio`, `Departamento`. |
| `assets` | `Grupo`, `TipoEquipamento`, `Equipamento`, QR code. |
| `inspections` | `TipoServico`, `Periodicidade`, `ServicoTipoEquipamento`, `SecaoChecklist`, `ItemChecklist`, `Servico`, `RespostaChecklist`, `AcaoCorretiva`. |
| `reports` | `RelatorioGerado`, geracao/exportacao de relatorios. |
| `api` | Serializers, viewsets, urls versionadas. |

Essa divisao pode ser feita aos poucos. Nao precisa ser uma grande reescrita imediata.

### 3. Introduzir services para regras de negocio

Mover regras hoje dentro de views para services:

- `equipamentos/services.py`: criacao, atualizacao, QR code.
- `inspections/services.py`: criacao de servico, respostas, pontuacao, rascunhos.
- `calendar/services.py`: calculo de eventos.
- `reports/services.py`: metricas e geracao de PDF.

Beneficio:

- Views ficam mais finas.
- Regras podem ser testadas sem HTTP.
- Mobile e web reutilizam a mesma logica.

### 4. Usar serializers DRF explicitos

Criar serializers para:

- Equipamento list/detail.
- Perfil.
- Dashboard.
- TipoServico configurado.
- Checklist item.
- Servico create/update.
- RespostaChecklist.
- AcaoCorretiva.

Evitar `fields='__all__'` para contratos publicos.

Beneficio:

- API mais estavel.
- Melhor validacao.
- Documentacao automatica mais simples.

### 5. Adicionar schema OpenAPI

Usar ferramenta como `drf-spectacular` ou equivalente.

Beneficio:

- Documenta endpoints mobile.
- Ajuda frontend/mobile a validar contrato.
- Facilita testes e integracao.

### 6. Padronizar respostas de API

Definir um envelope unico, por exemplo:

```json
{
  "success": true,
  "data": {},
  "meta": {},
  "errors": []
}
```

Ou seguir padrao DRF puro, evitando misturar envelopes diferentes.

### 7. Centralizar permissoes

Criar permissions DRF e helpers web para:

- Gestor/admin.
- Usuario comum.
- Escopo por predio.
- Escopo por departamento.
- Escopo por site.

Beneficio:

- Evita regras duplicadas entre `gestor_required`, `user_passes_test`, `IsGestorForWrites` e condicionais manuais.

### 8. Transacoes em fluxos criticos

Usar `transaction.atomic()` em:

- Criacao/atualizacao de servico com respostas.
- Criacao de acao corretiva.
- Alteracoes em tipo de equipamento + servicos + checklist.
- Exclusoes em cascata feitas por endpoints administrativos.

Beneficio:

- Evita estado parcial.
- Facilita consistencia no PostgreSQL.

### 9. Melhorar settings por ambiente

Separar configuracao:

- `settings/base.py`
- `settings/local.py`
- `settings/production.py`

Ou usar variaveis de ambiente diretamente.

Configuracoes recomendadas:

- `SECRET_KEY` via env.
- `DEBUG` via env.
- `ALLOWED_HOSTS` via env.
- `CSRF_TRUSTED_ORIGINS` via env.
- `DATABASE_URL` ou variaveis `POSTGRES_*`.
- `SITE_URL` para QR codes e URLs absolutas.

### 10. Preparar PostgreSQL formalmente

Passos sugeridos:

1. Criar `requirements.txt` ou `pyproject.toml`.
2. Adicionar `psycopg` ou `psycopg2-binary` conforme estrategia.
3. Parametrizar `DATABASES`.
4. Rodar testes contra PostgreSQL em ambiente local ou CI.
5. Validar dados existentes com comandos de auditoria.
6. Criar data migrations se forem remover campos legados.
7. Revisar constraints nullable e indexes.

### 11. Revisar indices

Adicionar indices conforme volume, especialmente em:

- `Equipamento(ativo, predio, departamento, tipo_equipamento, grupo)`.
- `Servico(status, criado_em)`.
- `Servico(equipamento, tipo_servico, status, criado_em)`.
- `RespostaChecklist(opcao)`.
- `ServicoTipoEquipamento(tipo_equipamento, tipo_servico, ativo)`.
- `SecaoChecklist(servico_tipo_equipamento, ativo, ordem)`.
- `ItemChecklist(secao, ativo, ordem)`.

### 12. Remover ou isolar codigo legado

Prioridades:

- Remover views nao roteadas que usam campos inexistentes, ou atualiza-las para o modelo atual.
- Remover duplicidade logica em `api_acoes_corretivas_criar`.
- Decidir destino de `Inspecao`.
- Decidir destino de `numero_extintor` e `numero_cilindro`.

### 13. Melhorar geracao de QR code

Proposta:

- Remover URL hardcoded do `save()`.
- Usar `settings.SITE_URL`.
- Criar service `generate_equipment_qr(equipamento)`.
- Criar management command para regenerar QR codes.

Beneficio:

- Evita QR code apontando para localhost em producao.
- Facilita ngrok/dev/prod.

### 14. Registrar models operacionais no admin

Adicionar admin para:

- `ServicoTipoEquipamento`
- `SecaoChecklist`
- `ItemChecklist`
- `Servico`
- `RespostaChecklist`
- `AcaoCorretiva`
- `RelatorioGerado`
- `Inspecao`, se continuar existindo.

Beneficio:

- Operacao e suporte ficam mais simples.
- Ajuda a depurar dados depois da migracao para PostgreSQL.

### 15. Ampliar testes

Testes recomendados:

- API DRF login, perfil e dashboard.
- QR code parsing.
- Criacao mobile de servico com JSON.
- Criacao mobile de servico com multipart e fotos.
- Permissoes por perfil.
- Rotas sombreadas em `/api/`.
- Calculo de calendario.
- Calculo de pontuacao.
- Relatorios e historico.
- Queries com dados sem relacionamento opcional.
- Test suite contra PostgreSQL.

## Prioridades recomendadas

### Curto prazo

1. Separar rotas `/web-api/` e `/api/v1/` para acabar com sombreamento.
2. Criar serializers explicitos para endpoints mobile.
3. Corrigir `ServicoCriarAPI` para aceitar multipart com `respostas` em JSON string e salvar fotos.
4. Parametrizar `baseURL` do mobile.
5. Criar `requirements.txt`.
6. Tirar `SECRET_KEY`, `DEBUG` e hosts de valores hardcoded.

### Medio prazo

1. Introduzir services para servicos/checklist/calendario/relatorios.
2. Adicionar transacoes nos fluxos criticos.
3. Revisar constraints nullable e indices.
4. Registrar models operacionais no admin.
5. Remover codigo legado nao roteado.

### Antes de migrar para PostgreSQL em producao

1. Instalar driver PostgreSQL e parametrizar settings.
2. Rodar migrations em banco PostgreSQL limpo.
3. Rodar testes contra PostgreSQL.
4. Fazer auditoria de dados no SQLite real.
5. Planejar migracao de media.
6. Regenerar QR codes com dominio correto.
7. Validar performance de calendario/dashboard/relatorios com volume esperado.

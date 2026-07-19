# Migracao PostgreSQL, producao e SaaS - Fase 0

Data da auditoria: 2026-06-06

## Escopo

Esta fase documenta o estado atual do NotchFire antes de qualquer mudanca de codigo para PostgreSQL, producao ou SaaS multiempresa.

Nao foram alterados settings, models, URLs, serializers, codigo mobile ou migrations nesta fase.

## Artefatos de seguranca

Backup versionado criado:

```text
backups/postgresql_saas_fase0_20260606_031748/db.sqlite3
```

Checksum SHA-256 registrado em:

```text
backups/postgresql_saas_fase0_20260606_031748/db.sqlite3.sha256
```

Valor:

```text
84c91373663e2fa03c9ef8c7ab8aa4ff939b763ada91de29e094053625b1c27b
```

Outros artefatos gerados:

- `backups/postgresql_saas_fase0_20260606_031748/model-counts.json`
- `backups/postgresql_saas_fase0_20260606_031748/media-files.txt`
- `backups/postgresql_saas_fase0_20260606_031748/pip-freeze.txt`
- `backups/postgresql_saas_fase0_20260606_031748/routes.txt`
- `backups/postgresql_saas_fase0_20260606_031748/route-resolution.txt`

Observacao: `shasum` emitiu aviso de locale do Perl, mas gerou o checksum corretamente.

## Comandos executados

Executados em `backend/`:

```bash
./venv/bin/python --version
./venv/bin/python -m django --version
./venv/bin/pip freeze
./venv/bin/python manage.py check
./venv/bin/python manage.py showmigrations
./venv/bin/python manage.py test
```

Resultados:

- Python: `3.14.3`
- Django: `6.0.3`
- `manage.py check`: passou sem issues.
- `manage.py test`: passou, 4 testes.
- `showmigrations`: migrations aplicadas em `core` ate `0011_relatoriogerado_equipamento`.

Dependencias instaladas no venv:

```text
asgiref==3.11.1
Django==6.0.3
djangorestframework==3.17.1
pillow==12.1.1
qrcode==8.2
sqlparse==0.5.5
```

Nao ha `backend/requirements.txt` atual. Nao ha `psycopg`, `gunicorn`, `uvicorn` ou `whitenoise` instalados ainda.

## Estado atual do backend

Arquivos inspecionados:

- `backend/notchfire_project/settings.py`
- `backend/notchfire_project/urls.py`
- `backend/core/models.py`
- `backend/core/views.py`
- `backend/core/views_api.py`
- `backend/core/urls.py`
- `backend/core/urls_api.py`
- `backend/core/serializers.py`
- `mobile/src/services/api.ts`
- `backend/core/migrations/`

Configuracao atual em `settings.py`:

- `SECRET_KEY` esta hardcoded.
- `DEBUG = True`.
- `ALLOWED_HOSTS` esta hardcoded com localhost, IP local e ngrok.
- `CSRF_TRUSTED_ORIGINS` esta hardcoded para ngrok.
- Banco atual usa SQLite em `BASE_DIR / "db.sqlite3"`.
- `TIME_ZONE = "UTC"`.
- `STATIC_URL = "static/"`.
- Nao existe `STATIC_ROOT`.
- `MEDIA_ROOT = BASE_DIR / "media"`.
- REST Framework usa TokenAuthentication por padrao.
- Nao existe `SITE_URL`.
- QR Code em `Equipamento.save()` usa URL hardcoded `http://127.0.0.1:8000/equipamentos/<id>/`.

Projeto de URLs:

- `backend/notchfire_project/urls.py` inclui `core.urls` em `""`.
- Tambem inclui `core.urls_api` em `"api/"`.
- `core.urls` contem muitos endpoints AJAX em `/api/...`.
- `core.urls_api` tambem expoe DRF em `/api/...`.

Mobile:

- `mobile/src/services/api.ts` usa `baseURL: "http://127.0.0.1:8000/api/"`.
- Ainda nao ha `.env.example` mobile para `EXPO_PUBLIC_API_URL`.

## Contagem de registros

Contagens registradas em `model-counts.json`:

```text
admin.LogEntry: 0
auth.Group: 0
auth.Permission: 96
auth.User: 5
authtoken.Token: 1
authtoken.TokenProxy: 1
contenttypes.ContentType: 24
core.AcaoCorretiva: 0
core.Departamento: 2
core.Equipamento: 1
core.Grupo: 2
core.Inspecao: 0
core.ItemChecklist: 2
core.Periodicidade: 1
core.Predio: 1
core.RelatorioGerado: 8
core.RespostaChecklist: 5
core.SecaoChecklist: 1
core.Servico: 7
core.ServicoTipoEquipamento: 1
core.TipoEquipamento: 3
core.TipoServico: 1
core.UsuarioPerfil: 4
sessions.Session: 59
```

## Media

Inventario completo salvo em:

```text
backups/postgresql_saas_fase0_20260606_031748/media-files.txt
```

Resumo:

- total de arquivos em `backend/media`: 32
- arquivos de QR Code: 26
- tamanho aproximado de `backend/media`: 10 MB
- tamanho aproximado de `backend/db.sqlite3`: 448 KB pelo `du`; copia do backup com 409600 bytes em `ls`.

Pastas encontradas:

- `backend/media/equipamentos/`
- `backend/media/qrcodes/`
- `backend/media/usuarios/`

## Migrations existentes

Migrations do `core`:

- `0001_initial`
- `0002_alter_equipamento_options_remove_equipamento_peso_and_more`
- `0003_secaochecklist_tipoequipamento_periodicidade_and_more`
- `0004_alter_periodicidade_tipo`
- `0005_secaochecklist_tipo_equipamento_and_more`
- `0006_servico_respostachecklist_acaocorretiva`
- `0007_alter_servicotipoequipamento_unique_together_and_more`
- `0008_alter_itemchecklist_secao`
- `0009_usuarioperfil_foto_usuarioperfil_predio`
- `0010_relatoriogerado`
- `0011_relatoriogerado_equipamento`

Todas estao aplicadas no SQLite atual.

## Rotas duplicadas ou sombreadas

Lista completa em `routes.txt`.

Duplicidade exata encontrada:

- `api/servicos/criar/`
- `^media/(?P<path>.*)$` em DEBUG, porque `notchfire_project.urls` e `core.urls` adicionam static/media.

Resolucao real de rotas criticas:

```text
/api/servicos/criar/ -> api_servicos_criar -> core.views.api_servicos_criar
/api/equipamentos/ -> api_equipamentos_listar -> core.views.api_equipamentos_listar
/api/login/ -> api-login -> core.views_api.view
/api/mobile/servicos/criar/ -> api-mobile-servicos-criar -> core.views_api.view
/api/equipamentos/1/tipos-servico/ -> api-equipamento-tipos-servico -> core.views_api.view
/api/qr/equipamento/ -> api-qr-equipamento -> core.views_api.view
```

Risco principal: como `core.urls` e incluido em `""` antes de `core.urls_api` em `"api/"`, endpoints AJAX web em `/api/...` podem sombrear endpoints DRF com o mesmo caminho. O exemplo confirmado e `/api/servicos/criar/`, que resolve para a view web `core.views.api_servicos_criar`, nao para `ServicoCriarAPI`.

## Campos e views legadas

Campos legados mantidos:

- `Equipamento.numero_extintor`
- `Equipamento.numero_cilindro`
- model `Inspecao`

Views/trechos legados com risco:

- `editor_tipo_equipamento_view` usa `SecaoChecklist.objects.filter(tipo_equipamento=tipo_equipamento, ativo=True)`, mas o model atual nao possui campo `tipo_equipamento`.
- Alguns endpoints legados usam filtros `tipo_equipamento_id=tipo_id` em `SecaoChecklist`, tambem sem campo atual no model.
- `serializers.py` expoe `EquipamentoSerializer` com `fields = "__all__"`, inadequado para contrato publico versionado.
- `views_api.ServicoCriarAPI` ainda nao trata multipart/fotos do checklist.

## Estado SaaS atual

Nao existem ainda:

- model `Empresa`
- model `EmpresaUsuario`
- coluna `empresa_id` nas entidades de negocio
- resolvedor central de tenant
- middleware de empresa ativa
- permission DRF por empresa
- filtros obrigatorios por empresa em queries
- testes de isolamento entre empresas

Documento ja existente de auditoria SaaS:

```text
docs/saas_multiempresa.md
```

## Riscos principais

- SQLite original ainda e a unica base de dados; migracao para PostgreSQL precisa preservar dados e media.
- Settings atuais nao estao prontos para producao por `SECRET_KEY`, `DEBUG`, hosts e CSRF hardcoded.
- `STATIC_ROOT` ausente impede fluxo normal de `collectstatic`.
- Media fica em filesystem local; producao precisa volume persistente ou storage externo.
- Mobile aponta para IP local fixo.
- APIs web e mobile compartilham `/api/`, criando rotas ambiguas.
- QR Code usa ID sequencial e URL local hardcoded.
- Tokens mobile antigos nao devem ser migrados automaticamente.
- Unicidades globais atuais em campos como `nome` e `numero_serie` conflitam com SaaS multiempresa.
- Queries de negocio usam `.all()`, `.filter()` e `get_object_or_404()` sem escopo de empresa.
- Admin, forms e serializers podem vazar dados entre empresas se receberem apenas `empresa_id` sem scoping.
- `TIME_ZONE = "UTC"` pode gerar divergencias operacionais no Brasil se filtros por data continuarem usando `__date`.

## Plano em fases

### Fase 1 - Dependencias e PostgreSQL local

- Criar `backend/requirements.txt` a partir das versoes instaladas.
- Adicionar `psycopg[binary]`.
- Avaliar `gunicorn`, `uvicorn` e `whitenoise`.
- Criar `backend/.env.example`.
- Atualizar settings por env mantendo fallback SQLite com `DB_ENGINE=sqlite`.
- Adicionar `STATIC_ROOT`, `SITE_URL`, flags de HTTPS/cookies e PostgreSQL configuravel.
- Criar `docker-compose.yml` para Postgres local.
- Validar SQLite e PostgreSQL local com `check`, `test`, `migrate`.

### Fase 2 - Scripts seguros SQLite para PostgreSQL

- Criar `scripts/export_sqlite_data.sh`.
- Criar `scripts/import_postgres_data.sh`.
- Criar management command `auditar_dados`.
- Exportar fixtures com exclusoes seguras.
- Copiar media junto com backup.
- Criar testes do comando de auditoria.

### Fase 3 - Separar API web e mobile

- Migrar AJAX web para `/web-api/...`.
- Versionar DRF mobile em `/api/v1/...`.
- Atualizar JS web e mobile.
- Criar `mobile/.env.example`.
- Testar que endpoints mobile nao caem em HTML de login.

### Fase 4 - Contrato mobile e transacoes

- Corrigir multipart/fotos em `ServicoCriarAPI`.
- Criar serializers DRF explicitos.
- Usar `transaction.atomic()` em fluxos criticos.
- Padronizar respostas da API versionada.

### Fase 5 - SaaS multiempresa

- Criar `Empresa` e `EmpresaUsuario`.
- Adicionar `empresa` nullable nos models de negocio.
- Criar empresa padrao para dados existentes.
- Fazer backfill.
- Ajustar constraints por empresa.
- Resolver empresa ativa na web e mobile.
- Aplicar scoping por empresa em views, DRF, dashboard, calendario, relatorios, QR e admin.
- Criar testes de isolamento.

### Fase 6 - Indices e timezone

- Adicionar indices compostos para consultas reais.
- Evitar `__date` quando prejudicar indices.
- Avaliar `TIME_ZONE = "America/Sao_Paulo"` com `USE_TZ=True`.

### Fase 7 - Producao

- Settings seguros para deploy.
- `collectstatic`.
- WhiteNoise apenas para static, se adotado.
- Volume persistente ou storage externo para media.
- Dockerfile/entrypoint/healthcheck.
- Backup e restore PostgreSQL/media documentados.

### Fase 8 - Relatorio final

- Criar `docs/relatorio_migracao_saas.md`.
- Registrar comandos finais, migrations, scripts, testes, rollback, contagens antes/depois e riscos restantes.

## Checklist de rollback

Antes de qualquer fase que altere codigo ou banco:

- criar backup novo de `backend/db.sqlite3`;
- registrar checksum SHA-256;
- registrar contagens por model;
- registrar lista de media;
- garantir que `manage.py check` passa;
- garantir que testes atuais passam.

Rollback da Fase 0:

- remover `docs/migracao_postgresql_saas.md`, se necessario;
- manter ou remover manualmente `backups/postgresql_saas_fase0_20260606_031748/`, conforme decisao operacional.

Rollback das fases futuras:

- se settings por env quebrarem SQLite, voltar `DB_ENGINE=sqlite` e restaurar settings da fase anterior;
- se migrations PostgreSQL falharem, descartar banco PostgreSQL local e recriar a partir das migrations;
- se importacao falhar, recriar PostgreSQL local, rodar migrations e importar novamente a fixture;
- se backfill SaaS falhar, voltar para o backup SQLite anterior e revisar data migration;
- nunca usar `flush`, `DROP DATABASE`, `TRUNCATE` ou exclusoes destrutivas sem confirmacao explicita;
- nunca apagar `backend/db.sqlite3` original durante a migracao.

## Comandos para desenvolvimento

Linha de base SQLite:

```bash
cd backend
./venv/bin/python manage.py check
./venv/bin/python manage.py test
./venv/bin/python manage.py showmigrations
```

Backup manual seguro:

```bash
mkdir -p ../backups
cp db.sqlite3 "../backups/db.sqlite3.$(date +%Y%m%d_%H%M%S).bak"
shasum -a 256 db.sqlite3
find media -type f -print | sort
```

Depois da Fase 1, PostgreSQL local esperado:

```bash
docker compose up -d postgres
docker compose ps
cd backend
DB_ENGINE=postgresql ./venv/bin/python manage.py migrate
DB_ENGINE=postgresql ./venv/bin/python manage.py check
DB_ENGINE=postgresql ./venv/bin/python manage.py test
```

## Fase 1 executada - configuracao PostgreSQL local

Data da execucao: 2026-06-06

Arquivos adicionados:

- `backend/requirements.txt`
- `backend/.env.example`
- `docker-compose.yml`

Arquivos alterados:

- `backend/notchfire_project/settings.py`

Backup criado antes das alteracoes da fase:

```text
backups/postgresql_fase1_20260606_165359/db.sqlite3
```

Dependencias instaladas e fixadas:

```text
Django==6.0.3
djangorestframework==3.17.1
pillow==12.1.1
qrcode==8.2
psycopg[binary]==3.3.4
gunicorn==26.0.0
uvicorn==0.49.0
whitenoise==6.12.0
```

O arquivo `requirements.txt` tambem fixa dependencias transitivas instaladas no ambiente atual.

Configuracoes adicionadas:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `SITE_URL`
- `DB_ENGINE=sqlite|postgresql`
- `DB_CONN_MAX_AGE`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- flags de HTTPS/cookies/HSTS por env
- `STATIC_ROOT`
- `MEDIA_ROOT` configuravel por env

Na Fase 1, o SQLite continuava sendo o default quando `DB_ENGINE` nao era
informado. A partir da Fase 2, o default operacional passou a ser PostgreSQL
e o backend carrega `backend/.env` automaticamente.

Validacao de configuracao PostgreSQL:

```bash
cd backend
./venv/bin/python manage.py check
```

Subida local do PostgreSQL, quando Docker estiver instalado:

```bash
docker compose --env-file backend/.env up -d postgres
docker compose ps
cd backend
./venv/bin/python manage.py migrate
./venv/bin/python manage.py check
DB_ENGINE=sqlite ./venv/bin/python manage.py test
```

Resultado na maquina atual:

- `docker` nao esta instalado ou nao esta no PATH: `docker: command not found`.
- `DB_ENGINE=postgresql ./venv/bin/python manage.py check` passou.
- `DB_ENGINE=postgresql ./venv/bin/python manage.py migrate --noinput` falhou por ausencia de servidor PostgreSQL em `localhost:5432`.

Validacoes SQLite executadas apos a alteracao:

```bash
cd backend
./venv/bin/python manage.py check
./venv/bin/python manage.py test
```

Resultados:

- `check`: passou sem issues.
- `test`: passou, 4 testes.

`check --deploy` foi executado e ainda aponta pendencias de producao quando usado com defaults de desenvolvimento. Isso e esperado ate configurar valores reais para chave secreta, HTTPS, cookies seguros e HSTS.

## Comandos para producao

Estes comandos sao planejados para fases futuras e nao devem ser executados ate settings, scripts e deploy estarem prontos:

```bash
cd backend
./venv/bin/python manage.py check --deploy
./venv/bin/python manage.py collectstatic --noinput
./venv/bin/python manage.py migrate
```

Backup PostgreSQL planejado:

```bash
pg_dump "$DATABASE_URL" > "backups/postgres_$(date +%Y%m%d_%H%M%S).sql"
```

Restore PostgreSQL planejado em ambiente controlado:

```bash
psql "$DATABASE_URL" < backups/postgres_<timestamp>.sql
```

Media em producao deve ser preservada separadamente do banco, por volume persistente ou storage externo.

## Fase 2 executada - PostgreSQL direto e base SaaS

Data da execucao: 2026-06-08

Arquivos adicionados:

- `.gitignore`
- `backend/.env`
- `backend/core/middleware.py`
- `backend/core/tenant_context.py`
- `backend/core/tenancy.py`
- `backend/core/migrations/0012_empresa_empresausuario_alter_departamento_nome_and_more.py`
- `backend/core/migrations/0013_backfill_empresa_padrao.py`

Arquivos alterados:

- `README.md`
- `docker-compose.yml`
- `backend/.env.example`
- `backend/core/admin.py`
- `backend/core/models.py`
- `backend/core/serializers.py`
- `backend/core/tests.py`
- `backend/core/views.py`
- `backend/core/views_api.py`
- `backend/notchfire_project/settings.py`
- `docs/iniciar.md`
- `docs/migracao_postgresql_saas.md`
- `docs/saas_multiempresa.md`

Mudancas principais:

- `settings.py` carrega `backend/.env` automaticamente.
- `DB_ENGINE` agora usa `postgresql` como default operacional.
- `DATABASE_URL` passa a ser aceito para provedores SaaS.
- WhiteNoise foi ativado para servir static files em producao.
- `Empresa` e `EmpresaUsuario` foram criados.
- Os models de negocio receberam `empresa` nullable com backfill para `Empresa Padrao`.
- Novos registros tenant-aware recebem a empresa ativa automaticamente durante requests web/API.
- Queries via manager padrao dos models de negocio filtram pela empresa ativa quando ela existe.
- APIs DRF com token ativam empresa depois da autenticacao.
- Unicidades globais principais viraram constraints por empresa: nomes de cadastros e numero de serie de equipamento.
- QR Code de equipamento usa `SITE_URL` em vez de URL local hardcoded.

Backup criado antes de aplicar as migrations no SQLite local:

```text
backups/postgresql_saas_fase2_20260608_121851/db.sqlite3
SHA-256: 8a681c2d33045944b7428a5bcd4480a1646be5beb96de5dea4640ebe00f20004
```

Validacoes executadas:

```bash
cd backend
./venv/bin/python manage.py check
DB_ENGINE=sqlite ./venv/bin/python manage.py check
DB_ENGINE=sqlite ./venv/bin/python manage.py makemigrations --check --dry-run
DB_ENGINE=sqlite ./venv/bin/python manage.py migrate
DB_ENGINE=sqlite ./venv/bin/python manage.py test
DB_ENGINE=sqlite ./venv/bin/python manage.py collectstatic --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY=uma-chave-de-producao-com-tamanho-suficiente-para-check DJANGO_ALLOWED_HOSTS=notchfire.example.com DJANGO_CSRF_TRUSTED_ORIGINS=https://notchfire.example.com DJANGO_SESSION_COOKIE_SECURE=True DJANGO_CSRF_COOKIE_SECURE=True DJANGO_SECURE_SSL_REDIRECT=True DJANGO_SECURE_HSTS_SECONDS=31536000 DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True DJANGO_SECURE_HSTS_PRELOAD=True ./venv/bin/python manage.py check --deploy
```

Resultados:

- `check`: passou sem issues no modo PostgreSQL configurado por `.env`.
- `makemigrations --check --dry-run`: sem migrations pendentes.
- `migrate` em SQLite: aplicou `0012` e `0013`.
- `test`: passou, 9 testes.
- `collectstatic`: copiou 197 arquivos e processou 186.
- `check --deploy`: passou com flags de producao.

Limite de validacao local:

- `docker` continua ausente ou fora do PATH nesta maquina.
- A migration real em PostgreSQL deve ser executada quando houver um servidor PostgreSQL acessivel.

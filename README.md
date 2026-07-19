# NotchFire

Projeto organizado para producao com Docker Compose:

- `backend/`: aplicacao Django servida por Gunicorn.
- `mobile/`: app Expo/React Native, separado do servidor e nao executado no Docker.
- `docker/nginx/`: configuracao do Nginx como proxy reverso.
- `docs/`: documentacao complementar do projeto.
- `docker-compose.yml`: stack de producao com `nginx`, `django` e `postgres`.

## Estrutura Docker

```text
.
|-- .env.example
|-- .dockerignore
|-- docker-compose.yml
|-- backend/
|   |-- Dockerfile
|   |-- entrypoint.sh
|   |-- manage.py
|   `-- notchfire_project/
|-- docker/
|   `-- nginx/
|       `-- conf.d/
|           `-- notchfire.conf
|-- docs/
`-- mobile/
```

## Servicos

- `postgres`: banco PostgreSQL persistente em volume Docker.
- `django`: backend Django com Gunicorn, migracoes automaticas e `collectstatic`.
- `nginx`: proxy reverso HTTP, servindo `/static/`, `/media/` e encaminhando o resto para o Django.

O app mobile nao entra nesta stack. Ele deve apontar para a URL publica da API depois que o servidor estiver online.

## Primeira execucao em producao

No Ubuntu Server, na raiz do projeto:

```bash
cp .env.example .env
```

Edite o `.env` e troque pelo menos:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `SITE_URL`
- `TENANT_BASE_DOMAINS`, quando usar subdominios por empresa

Depois construa e suba:

```bash
docker compose build
docker compose up -d
```

Na primeira subida, o container `django` espera o PostgreSQL ficar pronto, roda:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

e inicia:

```bash
gunicorn notchfire_project.wsgi:application
```

## Comandos de operacao

Subir a stack em segundo plano:

```bash
docker compose up -d
```

Parar e remover os containers sem apagar dados:

```bash
docker compose down
```

Nao use `docker compose down -v` em producao, porque isso remove os volumes e pode apagar o banco.

Ver logs de todos os servicos:

```bash
docker compose logs
```

Acompanhar logs em tempo real:

```bash
docker compose logs -f
```

Ver logs de um servico especifico:

```bash
docker compose logs -f django
docker compose logs -f nginx
docker compose logs -f postgres
```

Baixar imagens novas do Nginx e PostgreSQL:

```bash
docker compose pull
```

Rebuildar a imagem local do Django depois de alteracoes no backend:

```bash
docker compose build django
```

Rebuildar tudo:

```bash
docker compose build
```

Reiniciar toda a stack:

```bash
docker compose restart
```

Reiniciar somente um servico:

```bash
docker compose restart django
docker compose restart nginx
docker compose restart postgres
```

Aplicar atualizacoes depois de `pull` ou `build`:

```bash
docker compose up -d
```

## Healthcheck

Todos os containers possuem healthcheck:

- `postgres`: usa `pg_isready`.
- `django`: consulta `http://127.0.0.1:8000/healthz/`.
- `nginx`: consulta `http://127.0.0.1/healthz/`.

Para conferir:

```bash
docker compose ps
```

## Volumes persistentes

Os dados persistentes ficam em volumes nomeados:

- `notchfire_postgres_data`: dados do PostgreSQL.
- `notchfire_static_data`: arquivos estaticos coletados pelo Django.
- `notchfire_media_data`: uploads e arquivos de media.
- `notchfire_django_logs`: logs em arquivo do Django.
- `notchfire_nginx_logs`: logs do Nginx.

O PostgreSQL permanece persistente enquanto o volume `notchfire_postgres_data` existir.

## Variaveis principais

O Docker Compose usa o arquivo `.env` da raiz.

Banco:

```env
DB_ENGINE=postgresql
POSTGRES_DB=notchfire
POSTGRES_USER=notchfire
POSTGRES_PASSWORD=troque-esta-senha
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

Django:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=troque-por-uma-chave-grande-e-aleatoria
DJANGO_ALLOWED_HOSTS=seu-dominio.com,www.seu-dominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com
SITE_URL=https://seu-dominio.com
```

SaaS multiempresa:

```env
TENANT_BASE_DOMAINS=seu-dominio.com
TENANT_RESERVED_SUBDOMAINS=www,app,api,admin,static,media
```

Com `TENANT_BASE_DOMAINS=seudominio.com`, subdominios como `cliente.seudominio.com` podem ser resolvidos como empresas diferentes pela camada multiempresa do backend.

## CasaOS

No CasaOS, importe ou cole o conteudo do `docker-compose.yml` como uma stack do NotchFire e mantenha o `.env` na raiz do projeto no servidor.

Recomendacoes:

- publique somente o Nginx na porta `80`;
- nao publique o PostgreSQL na internet;
- mantenha backups regulares do volume `notchfire_postgres_data`;
- use `docker compose logs -f` pelo terminal quando precisar diagnosticar migracoes, Gunicorn ou banco.

## HTTPS futuro

A stack esta pronta para receber HTTPS depois.

Opcoes comuns:

- terminar TLS no proxy/reverse proxy do CasaOS e encaminhar para `nginx:80`;
- ou adicionar certificados ao Nginx em `docker/nginx/certs/` e habilitar um bloco `listen 443 ssl`.

Quando HTTPS estiver ativo, ajuste o `.env`:

```env
SITE_URL=https://seu-dominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
```

Ative HSTS somente quando tiver certeza de que o dominio e subdominios sempre usarao HTTPS.

## Comandos Django uteis

Criar superusuario:

```bash
docker compose exec django python manage.py createsuperuser
```

Rodar migracoes manualmente:

```bash
docker compose exec django python manage.py migrate
```

Coletar estaticos manualmente:

```bash
docker compose exec django python manage.py collectstatic --noinput
```

Abrir shell Django:

```bash
docker compose exec django python manage.py shell
```

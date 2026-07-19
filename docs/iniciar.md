Execucao automatica para desenvolvimento local:

```bash
./iniciar_projeto.sh
```

Esse comando cria/usa `backend/venv`, instala as dependencias do backend,
roda `npm install` no mobile, aplica migracoes e inicia Django + Expo. O modo
padrao usa SQLite local para facilitar a primeira execucao em outro computador.

Para validar sem abrir servidores:

```bash
./iniciar_projeto.sh --check-only
```

Para testar no Expo Go pela rede local:

```bash
./iniciar_projeto.sh --lan
```

Para compartilhar com alguem fora da sua rede:

```bash
ngrok http 8000
```

Copie a URL HTTPS gerada, por exemplo `https://...ngrok-free.app`, e em
outro terminal rode:

```bash
./iniciar_projeto.sh --tunnel --public-url URL_HTTPS_DO_NGROK
```

Com o `ngrok http 8000` aberto, o script tambem tenta detectar essa URL sozinho:

```bash
./iniciar_projeto.sh --tunnel
```

Envie a URL `/login/` do ngrok para acessar o site e o QR Code do Expo para
abrir o app no Expo Go. Enquanto a pessoa estiver testando, mantenha o ngrok e
o script abertos no seu computador.

Backend com PostgreSQL:

```bash
./iniciar_projeto.sh --postgres
```

Ou manualmente:

```bash
docker compose --env-file backend/.env up -d postgres
cd backend
./venv/bin/python manage.py migrate
./venv/bin/python manage.py runserver 127.0.0.1:8000
```

Backend sem Docker, usando PostgreSQL externo:

```bash
cd backend
export DATABASE_URL=postgresql://usuario:senha@host:5432/banco
./venv/bin/python manage.py migrate
./venv/bin/python manage.py runserver 127.0.0.1:8000
```

Validacao local temporaria em SQLite:

```bash
cd backend
DB_ENGINE=sqlite ./venv/bin/python manage.py test
```

Mobile:

```bash
cd mobile
npm start
```

Para testar pela rede local em vez de `127.0.0.1`, use:

```bash
cd backend
./venv/bin/python manage.py runserver 0.0.0.0:8000
```

Em outro terminal:

```bash
cd mobile
EXPO_PUBLIC_API_BASE_URL=http://SEU_IP:8000/api/ npx expo start --lan
```

Comando antigo direto do backend, mantido apenas como referencia local:

```bash
cd backend
./venv/bin/python manage.py runserver 127.0.0.1:8000
```

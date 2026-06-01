# Agenda OLS

Aplicação web responsiva para lançamento e gerenciamento de agendas, com React, Django REST Framework, JWT e PostgreSQL.

## Recursos implementados

- Login por e-mail e senha com JWT.
- Rotas protegidas no frontend.
- Perfis: Administrador, Chefe e Agente.
- CRUD de agendas com validação de conflito por responsável ou local.
- Controle de acesso no backend:
  - Administrador acessa e exclui tudo.
  - Chefe gerencia agendas da própria equipe.
  - Agente visualiza suas agendas e edita apenas pendentes criadas por ele.
- Histórico automático a cada criação/alteração de agenda.
- Dashboard com totais e próximas agendas.
- Calendário mensal, semanal e diário.
- Relatórios por período, status, equipe e usuário.
- Exportação para Excel e PDF.
- Cadastro administrativo de usuários.
- Layout responsivo com menu lateral no desktop e menu hambúrguer no mobile.

## Estrutura

```text
backend/
  apps/accounts/       usuários, login e permissões
  apps/schedules/      equipes, agendas, histórico e relatórios
  config/              settings, urls, ASGI/WSGI
frontend/
  src/api/             cliente HTTP
  src/components/      layout, filtros e cards
  src/pages/           telas principais
docker-compose.yml     PostgreSQL local
```

## Como rodar localmente

### 1. Banco de dados

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

A API ficará em `http://localhost:8000/api/`.

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

O app ficará em `http://localhost:5173/`.

## Usuários iniciais

Depois de executar `python manage.py seed_demo`:

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Administrador | admin@agenda.local | Admin@12345 |
| Chefe | supervisor@agenda.local | Supervisor@12345 |
| Agente | usuario@agenda.local | Usuario@12345 |

## Importar a planilha existente

Com o PostgreSQL configurado no `backend/.env`, rode:

```bash
cd backend
.venv\Scripts\activate
python manage.py import_agentes_workbook C:\Users\fferreira\Downloads\AGENTES.xlsx
```

O importador lê as abas auxiliares, cria/atualiza os cadastros normalizados e importa a aba `DADOS` para agendas. Ele usa o campo `ID` da planilha como `source_id`, então pode ser executado novamente sem duplicar as agendas.

## Endpoints principais

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET/POST /api/users/`
- `GET/POST /api/sectors/`
- `GET/POST /api/agendas/`
- `GET /api/agendas/dashboard/`
- `GET /api/reports/`
- `GET /api/reports/export_excel/`
- `GET /api/reports/export_pdf/`

## Observações para evolução

- A tela de recuperação de senha está preparada no fluxo visual; para produção, conecte `PasswordResetView`/e-mail transacional.
- Para ambientes reais, troque `SECRET_KEY`, use HTTPS, restrinja `ALLOWED_HOSTS`/CORS e configure backups do PostgreSQL.
- Os relatórios exportam os dados filtrados pelo mesmo escopo de permissão do usuário autenticado.

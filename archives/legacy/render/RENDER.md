# Deploy no Render

O repositorio inclui `render.yaml` para criar:

- `agenda-educacao-api`: backend Django.
- `agenda-educacao-web`: frontend estatico Vite.
- `agenda-educacao-db`: PostgreSQL.

No Render, use **New > Blueprint**, selecione este repositorio e confirme a criacao dos servicos.

Depois que os servicos forem criados, ajuste as variaveis:

- No backend `agenda-educacao-api`:
  - `FRONTEND_URL`: URL publica do static site, por exemplo `https://agenda-educacao-web.onrender.com`.
  - `CORS_ALLOWED_ORIGINS`: mesma URL do frontend.
  - `DJANGO_SUPERUSER_EMAIL`: e-mail inicial, por padrao `admin@agenda.local`.
  - `DJANGO_SUPERUSER_PASSWORD`: senha inicial. Se nao for definida, o padrao e `Admin@12345`.
  - `DJANGO_SUPERUSER_FULL_NAME`: nome exibido, por padrao `Admin Agenda`.
  - variaveis SMTP para disparo real de e-mail:
    - `EMAIL_BACKEND`: `django.core.mail.backends.smtp.EmailBackend`.
    - `EMAIL_HOST`: servidor SMTP do provedor.
    - `EMAIL_PORT`: normalmente `587` com TLS ou `465` com SSL.
    - `EMAIL_HOST_USER`: usuario da conta SMTP.
    - `EMAIL_HOST_PASSWORD`: senha SMTP ou app password.
    - `EMAIL_USE_TLS`: `True` para porta 587.
    - `EMAIL_USE_SSL`: `True` para porta 465; deixe `False` se usar TLS.
    - `DEFAULT_FROM_EMAIL`: remetente exibido, de preferencia a mesma conta autenticada.
    - `AGENDA_REPLY_TO_EMAIL`: endereco para respostas.
- No frontend `agenda-educacao-web`:
  - `VITE_API_URL`: URL da API com `/api`, por exemplo `https://agenda-educacao-api.onrender.com/api`.

O backend roda automaticamente `python manage.py bootstrap_admin` depois das migracoes. O comando e idempotente: ele cria o administrador se nao existir e garante que ele continue ativo, staff e superuser.

Por seguranca, depois do primeiro acesso em producao troque a senha ou defina `DJANGO_SUPERUSER_PASSWORD` no Render antes do deploy.

Para validar SMTP antes de usar os fluxos automaticos, rode no backend:

```bash
python manage.py test_email destino@exemplo.com
```

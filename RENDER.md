# Deploy no Render

O repositório inclui `render.yaml` para criar:

- `agenda-educacao-api`: backend Django.
- `agenda-educacao-web`: frontend estático Vite.
- `agenda-educacao-db`: PostgreSQL.

No Render, use **New > Blueprint**, selecione este repositório e confirme a criação dos serviços.

Depois que os serviços forem criados, ajuste as variáveis:

- No backend `agenda-educacao-api`:
  - `FRONTEND_URL`: URL pública do static site, por exemplo `https://agenda-educacao-web.onrender.com`.
  - `CORS_ALLOWED_ORIGINS`: mesma URL do frontend.
  - variáveis `EMAIL_*`, se houver SMTP real.
- No frontend `agenda-educacao-web`:
  - `VITE_API_URL`: URL da API com `/api`, por exemplo `https://agenda-educacao-api.onrender.com/api`.

Para criar o primeiro administrador em produção, abra o Shell do serviço backend e rode:

```bash
python manage.py createsuperuser
```

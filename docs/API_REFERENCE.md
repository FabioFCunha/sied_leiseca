# Documentação da API (SIED - Operação Lei Seca)

## Fiscalização — Relatório diário

`GET /api/inspection/statistics/daily-report/?date=AAAA-MM-DD`

Retorna os indicadores homologados da data solicitada e um comparativo anual independente do filtro. Sem `date`, o relatório diário utiliza a data da última operação aprovada. O comparativo sempre termina nessa última data e usa o mesmo dia e mês no ano anterior.

- `daily`: data, indicadores e produção por equipe;
- `comparison`: períodos explícitos, dias com operação e linhas com diferença, variação percentual e médias diárias;
- `meta.latest_operation_date`: última data homologada utilizada no comparativo.

Esta aplicação expõe os dados de negócio (Agendas, Relatórios, Metas e Ações) por meio de uma API construída sob a fundação do **Django Rest Framework (DRF)**.

**Importante:** Não gere documentações manuais extensas dos payloads aqui neste arquivo. O DRF é construído em cima de OpenAPI, o que permite introspecção e documentação auto-gerada que evolui juntamente com o código.

## 1. Módulos e Endpoints Principais

A arquitetura da API está dividida conceitualmente nos seguintes domínios:

1. **Authentication & Accounts (`/api/accounts/`):**
   - Gerencia a emissão de tokens JWT, controle de sessão, e informações do perfil do solicitante logado, aplicando os limites de segurança da infraestrutura de login do Django Auth.
   
2. **Schedules & Agendas (`/api/schedules/`):**
   - Base de marcação e tracking temporal. Expõe os endpoints de criação e fechamento das programações das equipes em vias e instituições.

3. **Education Actions & Reports (`/api/education/`):**
   - Engloba a submissão das operações de conscientização, volume de materiais distribuídos (avaliações, gibis) e impacto direto.

4. **Satisfaction Surveys & Goals (`/api/surveys/` / `/api/goals/`):**
   - Coleta de Feedback moderado (`ModerationStatus`) e metas de indicadores educacionais da corporação.

## 2. Como consultar a documentação ao vivo

A especificação exata (incluindo verbos HTTP válidos, payloads requeridos e serializers) pode ser acessada conectando na própria infraestrutura do backend rodando em modo desenvolvedor e inspecionando os endopints de Schema Auto-generated do DRF caso ativados, ou simplesmente lendo os arquivos `urls.py` e os ViewSets correspondentes de cada app em `backend/apps/*/urls.py`.

## 3. Padrão de Resposta

* A API impõe padronização RESTful (códigos `200/201` para sucesso, `400` para Bad Request de validação, `401/403` para bloqueios de autenticação).
* Erros retornam no formato padrão JSON do DRF ditando qual campo falhou (ex: `{"field_name": ["ErrorMessage"]}`).

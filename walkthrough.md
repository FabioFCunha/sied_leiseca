# Walkthrough - Etapa 3C - Relatorios Tecnicos no modo aplicativo

## Diagnostico final do fluxo
A Etapa 3C adicionou consulta mobile de Relatorios Tecnicos em modo somente leitura. A listagem usa exclusivamente `GET /education-reports/` e o detalhe usa exclusivamente `GET /education-reports/{id}/`. Nenhuma rota mobile executa POST, PUT, PATCH, DELETE, cache local ou armazenamento offline.

## Arquivos criados
- `frontend/src/pages/mobile/MobileReportsPage.jsx`
- `frontend/src/pages/mobile/MobileReportDetailsPage.jsx`
- `frontend/src/components/mobile/MobileReportCard.jsx`
- `frontend/src/components/mobile/MobileReportStatusBadge.jsx`

## Arquivos alterados
- `frontend/src/App.jsx`
- `frontend/src/components/mobile/MobileBottomNav.jsx`
- `frontend/src/pages/mobile/MobileMorePage.jsx`
- `frontend/src/pages/TechnicalReportsPage.jsx`
- `frontend/src/styles/mobile.css`
- `walkthrough.md`

## Rotas adicionadas
- `/app/relatorios`
- `/app/relatorios/:id`

## Endpoints utilizados
- `GET /education-reports/`
- `GET /education-reports/{id}/`
- `GET /education-reports/{id}/` tambem e usado pelo parametro desktop `?openReport={id}`.

## Filtros reais utilizados
Confirmados no `EducationReportViewSet.get_queryset()`:
- `status`: igualdade direta em `EducationReport.status`.
- `date_from`: `operation_date__gte`.
- `date_to`: `operation_date__lte`.
- `protocol`: igualdade direta em `agenda_id`.

Outros filtros existentes no backend, mas nao usados na UI mobile desta etapa: `team`, `source`, `date`, `q`.

## Significado exato de `protocol`
`protocol` filtra `EducationReport.agenda_id` por igualdade. O valor esperado e o ID numerico da Agenda. Pode retornar varios relatorios se houver mais de um relatorio autorizado vinculado a mesma Agenda.

## Filtro por Agenda
Foi comprovado que `protocol` recebe ID da Agenda. A listagem mobile aceita `?agenda=<agendaId>` e converte internamente para `protocol=<agendaId>` apenas quando o valor e numerico. Nao foi adicionado botao novo na tela `/app/agendas/:id` nesta etapa.

## Status implementados
- `DRAFT`: Rascunho
- `PENDING_REVIEW`: Enviado / Aguardando Conferencia
- `APPROVED`: Aprovado
- `RETURNED`: Devolvido
- status desconhecido: Status nao identificado

## Comportamento de USER e SUPPORT
A listagem mobile detecta `USER` e `SUPPORT` pelo usuario autenticado e mostra: "Seu perfil nao possui acesso aos Relatorios Tecnicos nesta versao do sistema." com botao "Voltar ao inicio". A interface nao tenta buscar por Agenda, Escala, usuario, equipe ou outro endpoint para contornar a regra do backend.

## Estrutura dos cartoes
O card mostra somente valores reais: data da operacao, Agenda, OS, equipe, local, status, atualizacao e chip de estatistica processada quando o campo vem verdadeiro. Nao mostra `null`, `undefined`, JSON bruto ou campos tecnicos sem utilidade operacional.

## Estrutura dos detalhes
O detalhe e somente leitura e mostra secoes condicionais: identificacao, local e solicitacao, participantes registrados, acoes executadas, materiais, devolucao e estatistica. Nao consulta Agenda, Escala, usuarios, agentes ou apoios para completar informacoes.

## Tratamento de acoes
`actions` e exibido como array recebido no relatorio, sem recalculo, sem revalidacao e sem exclusao por regra mobile.

## Tratamento de materiais
Os campos de materiais sao exibidos separadamente quando possuem valor real. Nao ha reclassificacao, mescla de categorias, migracao de taxonomia ou recalculo de totais.

## Tratamento de devolucao
Quando `status === RETURNED`, a tela mostra `review_notes` se o campo vier no payload. Nao existe acao mobile para responder, corrigir ou reenviar.

## Tratamento da estatistica
A tela separa status do relatorio e status da estatistica quando `statistics_processed` estiver presente no payload. Se verdadeiro, mostra processada e a data de `statistics_processed_at` quando disponivel. Se falso, mostra aguardando processamento. Nenhum `process-statistics` e chamado.

## Parametro escolhido para abertura direta
`/relatorio-tecnico?openReport={id}`.

## Funcao existente reutilizada
O desktop reutiliza o fluxo de estado ja usado pelo formulario: `setForm(report)` e `setEditing(report.id)`. O formulario nao foi copiado para o mobile.

## Forma de busca individual
O parametro `openReport` valida ID inteiro positivo e chama `api(`/education-reports/${reportId}/`, { redirectOnUnauthorized: false })`.

## Tratamento de 401, 403 e 404
Mobile e desktop deixam o backend validar acesso. Erros sao exibidos ao usuario sem inserir objetos nao autorizados no estado. `403` mostra ausencia de permissao; `404` mostra relatorio nao encontrado; `401` e tratado como sessao expirada/necessidade de nova autenticacao.

## Protecao contra execucao duplicada
O desktop usa `processedOpenReport` com `useRef`, marcando o ID antes da requisicao para evitar repeticao e duplicidade em re-renderizacao/Strict Mode.

## Remocao do parametro
Apos sucesso, erro ou ID invalido, `openReport` e removido com `setSearchParams(..., { replace: true })`. A remocao nao fecha o relatorio ja aberto.

## Confirmacoes
- O formulario desktop nao foi copiado.
- Nenhuma validacao de formulario foi duplicada no mobile.
- Nenhuma requisicao de escrita ocorre ao abrir relatorio pelo mobile ou pelo `openReport`.
- Nenhum endpoint novo foi criado.
- Nenhuma permissao foi ampliada.
- Nenhum backend, serializer, model ou migration foi alterado.
- `frontend/public/sw.js` nao foi alterado; a regra existente para ignorar `/api/*` foi preservada.
- As novas telas nao usam LocalStorage, SessionStorage, IndexedDB, Cache Storage ou arquivos locais.

## Resultado do build
`npm run build` executado com sucesso em `frontend`. O Vite concluiu o build e manteve apenas o aviso existente de chunks maiores que 500 kB.

## Resultado do lint
Nao ha script `lint` configurado no `frontend/package.json`; portanto lint nao foi executado.

## Resultado dos testes por role
Validacao estatica implementada para `USER` e `SUPPORT` com mensagem de ausencia de acesso, sem consulta alternativa. Roles autorizadas seguem para a API e respeitam `401`, `403`, `404`, falha de rede, lista vazia e paginacao. Testes com usuarios reais nao foram executados porque a sessao local de API autenticada/dados reais nao foi fornecida neste turno.

## Resultado dos testes mobile
Coberto por build e revisao de implementacao: `/app/relatorios`, `/app/relatorios/:id`, carregamento, vazio, erro, paginacao, carregar mais, atualizacao manual, filtros de status/data inicial/data final, status reais, status desconhecido, campos opcionais ausentes, textos longos com `overflow-wrap`, e barra inferior de cinco itens. Testes visuais em larguras 320, 360, 390, 412 e 768 px nao foram executados em navegador autenticado nesta etapa.

## Ausencia de cache da API
Confirmada por busca nos novos arquivos: nao ha uso de armazenamento local ou Cache Storage. O Service Worker existente continua com a regra de ignorar `/api/*`.

## Preservacao do desktop
A rota desktop sem parametro continua usando o fluxo existente. A abertura manual desktop continua no mesmo formulario. A unica alteracao funcional no desktop foi o tratamento de `openReport` por GET individual e remocao do parametro.

## Limitacoes encontradas
- O arquivo `walkthrough.md` nao existia no workspace no inicio; este arquivo foi criado na raiz para cumprir a entrega.
- O serializer atualmente visivel nao lista `statistics_processed`, `statistics_processed_at` e `review_notes`, embora os campos existam no model e tenham sido indicados no diagnostico da etapa. A UI esta preparada para exibi-los quando vierem no payload, sem alterar backend.
- Sem ambiente autenticado com dados reais, nao foi possivel executar a matriz completa de 63 cenarios em runtime.

## Pendencias futuras
- Frequencia editavel, formulario mobile completo, relatorio offline, sincronizacao offline, camera, GPS, notificacoes, aprovacao mobile e processamento estatistico permanecem fora desta etapa.
- Uma etapa futura pode adicionar botao em `/app/agendas/:id` para relatorios usando o filtro comprovado `protocol=<agendaId>`, se autorizado.
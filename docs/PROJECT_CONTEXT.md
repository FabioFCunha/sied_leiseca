# Contexto do Projeto: SIED (Operação Lei Seca)

O **Sistema de Informação de Educação (SIED)** é a plataforma central utilizada para gerenciar, auditar e planejar as frentes educacionais da Operação Lei Seca.

## 1. Visão Geral do Domínio de Negócio

A aplicação serve como pilar de acompanhamento de todas as **Ações Educativas** e **Agendas**. O objetivo macro é controlar a distribuição de equipes (palestrantes, testemunhos), auditar os relatórios de educação no trânsito e gerir o feedback dos eventos realizados em escolas, praias, bares e vias públicas.

## 2. Fluxo Operacional

O ecossistema é baseado em fluxos temporais de eventos:
* **Agendas (Agenda):** Planejamento futuro de onde a equipe da Lei Seca atuará, designando responsáveis, horários e localização (instituições).
* **Ações Educativas (EducationAction/EducationReport):** Onde o resultado de uma agenda se torna um relatório (Report) consolidado. Ele computa distribuição de materiais didáticos (gibis, folders, "cricris", "vetarolas") e quantas pessoas foram impactadas.
* **Pesquisas de Satisfação (SatisfactionSurvey):** Feedback coletado dos participantes/solicitantes com um sistema de Moderação e Auditoria (`ModerationStatus: PENDING, APPROVED, REJECTED`) para garantir a governança e a lisura dos comentários.
* **Metas Educacionais (EducationGoal):** Uma governança interna que define e acompanha os KPIs das ações executadas durante o ano.

## 3. Perfis e Restrições
A plataforma modela também restrições severas de acessibilidade (bloqueios e exceções) e regras rígidas de segurança por tipo de usuário (cidadãos, servidores, gestores) por meio do Django Auth.

## 4. O Sistema como Produto Vivo
O projeto lida com volumes imutáveis de mídia (fotos, relatórios) e um banco de dados relacional extremamente rico que nunca deve ser purgado (`root_postgres_data`). A evolução desse ecossistema deve sempre focar em estabilidade, disponibilidade (alta importância governamental) e zero quebras na base consolidada (migrations).

## 5. Fiscalização — Relatório Diário

O Relatório Diário apresenta somente a produção homologada na data escolhida. Seus cards são Abordados, Multados, Alcoolemia, Percentual, Fiscalizações e Recusas.

O comparativo anual da mesma tela é independente do filtro diário: compara 1º de janeiro até a data da última operação aprovada com o mesmo intervalo do ano anterior. O total comparável de alcoolemia soma Recusas, Art. 165 administrativo e Art. 306 criminal. As médias utilizam a quantidade de dias com operação, e não os dias corridos.

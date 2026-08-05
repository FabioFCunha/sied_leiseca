$sourcePath = 'C:\Users\FABIO CUNHA\.codex\visualizations\2026\07\24\019f93fd-4a0d-7321-b222-621e212ce8fc\painel-historico-acoes-educacao.html'
$targetPath = 'C:\Users\FABIO CUNHA\.codex\visualizations\2026\07\24\019f93fd-4a0d-7321-b222-621e212ce8fc\painel-historico-acoes-com-tabela.html'

$content = Get-Content -Raw -LiteralPath $sourcePath

$content = $content.Replace(
'    #ols-history-viz .note { border-left: 3px solid var(--viz-series-3); padding-left: .75rem; color: var(--muted-foreground); }',
'    #ols-history-viz .note { border-left: 3px solid var(--viz-series-3); padding-left: .75rem; color: var(--muted-foreground); }
    #ols-history-viz .indicator-table th { white-space: nowrap; }
    #ols-history-viz .indicator-table .new-indicator { border-left: 3px solid var(--viz-series-4); }
    #ols-history-viz .source-label { color: var(--muted-foreground); font-size: .875rem; }'
)

$tableMarkup = @'

  <section>
    <h3>Indicadores histÃ³ricos e alimentaÃ§Ã£o oficial</h3>
    <p class="text-muted">Leitura consolidada dos indicadores jÃ¡ utilizados pela instituiÃ§Ã£o e das novas categorias alimentadas pelo processo atual.</p>
    <div class="table-responsive">
      <table class="table table-sm indicator-table">
        <thead>
          <tr>
            <th>Indicador</th>
            <th class="text-end">HistÃ³rico atÃ© 2025</th>
            <th class="text-end"><span id="ols-table-base-year">2025</span></th>
            <th class="text-end">2026</th>
            <th class="text-end">VariaÃ§Ã£o</th>
            <th>AlimentaÃ§Ã£o oficial</th>
          </tr>
        </thead>
        <tbody id="ols-history-indicator-body"></tbody>
      </table>
    </div>
    <p class="note text-small">PraÃ§as/Parques PÃºblicos e Pontos turÃ­sticos passam a ter indicador prÃ³prio no novo processo. Como nÃ£o existiam de forma separada na base histÃ³rica, o histÃ³rico permanece zerado atÃ© que novos registros sejam classificados nessas opÃ§Ãµes.</p>
  </section>
'@

$content = $content.Replace(
'  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>',
$tableMarkup + "`r`n  <script src=`"https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js`"></script>"
)

$definitions = @'
      const indicatorDefinitions = [
        {label:'Palestras', key:'palestras', source:'ConsolidatedStatistic Â· tipo Palestra'},
        {label:'AÃ§Ãµes', key:'acoes', source:'ConsolidatedStatistic Â· tipo AÃ§Ã£o'},
        {label:'Bares', key:'bares', source:'Detalhamento da aÃ§Ã£o de rua'},
        {label:'PedÃ¡gio', key:'pedagio', source:'Detalhamento da aÃ§Ã£o de rua'},
        {label:'PraÃ§as Esportivas', key:'esportes', source:'Detalhamento da aÃ§Ã£o de rua'},
        {label:'Praia', key:'praia', source:'Detalhamento da aÃ§Ã£o de rua'},
        {label:'Eventos', key:'eventos', source:'Detalhamento da aÃ§Ã£o de rua'},
        {label:'Shopping/Centro Comerciais', key:'shopping', source:'Detalhamento da aÃ§Ã£o de rua'},
        {label:'PraÃ§as/Parques PÃºblicos', key:'parques', source:'Novo processo Â· detalhamento da aÃ§Ã£o de rua', isNew:true},
        {label:'Pontos turÃ­sticos', key:'turisticos', source:'Novo processo Â· detalhamento da aÃ§Ã£o de rua', isNew:true},
        {label:'Outros / nÃ£o classificado', key:'outros', source:'Detalhamento da aÃ§Ã£o de rua'}
      ];
'@

$content = $content.Replace(
'      const css = getComputedStyle(root);',
$definitions + '      const css = getComputedStyle(root);'
)

$renderCode = @'
      const historicalTotal = key => annual
        .filter(item => item.year <= 2025)
        .reduce((sum, item) => sum + Number(item[key] || 0), 0);
      const variation = (currentValue, baseValue) => {
        if (!baseValue) return currentValue ? 'Novo' : '0,0%';
        const value = ((currentValue - baseValue) / baseValue) * 100;
        const sign = value > 0 ? '+' : '';
        return `${sign}${value.toLocaleString('pt-BR', {minimumFractionDigits:1, maximumFractionDigits:1})}%`;
      };
      const renderIndicatorTable = () => {
        const selected = annual.find(item => item.year === Number(select.value));
        const tableBody = root.querySelector('#ols-history-indicator-body');
        root.querySelector('#ols-table-base-year').textContent = selected.year;
        tableBody.innerHTML = '';
        indicatorDefinitions.forEach(item => {
          const baseValue = Number(selected[item.key] || 0);
          const currentValue = Number(current[item.key] || 0);
          const row = document.createElement('tr');
          if (item.isNew) row.classList.add('new-indicator');
          row.innerHTML = `<td>${item.label}${item.isNew ? ' <span class="badge">Novo</span>' : ''}</td><td class="text-end">${format(historicalTotal(item.key))}</td><td class="text-end">${format(baseValue)}</td><td class="text-end">${format(currentValue)}</td><td class="text-end">${variation(currentValue, baseValue)}</td><td><span class="source-label">${item.source}</span></td>`;
          tableBody.appendChild(row);
        });
      };

'@

$content = $content.Replace(
'      const renderComparison = () => {',
$renderCode + '      const renderComparison = () => {'
)

$content = $content.Replace(
'        root.querySelector(''#ols-street-subtitle'').textContent = `Categorias da SolicitaÃƒÂ§ÃƒÂ£o Interna: ${selected.year} versus 2026.`;',
'        root.querySelector(''#ols-street-subtitle'').textContent = `Categorias da SolicitaÃƒÂ§ÃƒÂ£o Interna: ${selected.year} versus 2026.`;
        renderIndicatorTable();'
)

Set-Content -LiteralPath $targetPath -Value $content -Encoding utf8


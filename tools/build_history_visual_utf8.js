const fs = require('fs');

const sourcePath = String.raw`C:\Users\FABIO CUNHA\.codex\visualizations\2026\07\24\019f93fd-4a0d-7321-b222-621e212ce8fc\painel-historico-acoes-com-tabela.html`;
const targetPath = String.raw`C:\Users\FABIO CUNHA\.codex\visualizations\2026\07\24\019f93fd-4a0d-7321-b222-621e212ce8fc\painel-historico-completo-desde-2011.html`;

let content = fs.readFileSync(sourcePath, 'utf8').replace(/^\uFEFF/, '');
content = Buffer.from(content, 'latin1').toString('utf8');

const fullTable = `

  <section>
    <h3>Série histórica completa dos indicadores</h3>
    <p class="text-muted">Quantitativos anuais desde 2011, sem comparação percentual.</p>
    <div class="table-responsive">
      <table class="table table-sm indicator-table">
        <thead>
          <tr>
            <th>Ano</th>
            <th class="text-end">Palestras</th>
            <th class="text-end">Ações</th>
            <th class="text-end">Bares</th>
            <th class="text-end">Pedágio</th>
            <th class="text-end">Praças esportivas</th>
            <th class="text-end">Praia</th>
            <th class="text-end">Eventos</th>
            <th class="text-end">Shopping/centros comerciais</th>
            <th class="text-end">Praças/parques públicos</th>
            <th class="text-end">Pontos turísticos</th>
            <th class="text-end">Ação social</th>
            <th class="text-end">Outros</th>
          </tr>
        </thead>
        <tbody id="ols-complete-history-body"></tbody>
      </table>
    </div>
  </section>`;

content = content.replace(
  '  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>',
  `${fullTable}\n  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>`
);

const fullTableScript = `
      const completeHistoryBody = root.querySelector('#ols-complete-history-body');
      annual.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = \`<td>\${item.year}</td><td class="text-end">\${format(item.palestras)}</td><td class="text-end">\${format(item.acoes)}</td><td class="text-end">\${format(item.bares)}</td><td class="text-end">\${format(item.pedagio)}</td><td class="text-end">\${format(item.esportes)}</td><td class="text-end">\${format(item.praia)}</td><td class="text-end">\${format(item.eventos)}</td><td class="text-end">\${format(item.shopping)}</td><td class="text-end">\${format(item.parques)}</td><td class="text-end">\${format(item.turisticos)}</td><td class="text-end">\${format(item.social)}</td><td class="text-end">\${format(item.outros)}</td>\`;
        completeHistoryBody.appendChild(row);
      });
`;

content = content.replace(
  "      const body = root.querySelector('#ols-options-body');",
  `${fullTableScript}\n      const body = root.querySelector('#ols-options-body');`
);

fs.writeFileSync(targetPath, content, 'utf8');

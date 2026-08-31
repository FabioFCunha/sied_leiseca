export const ANNUAL_DISTRIBUTION_TOTAL_KEY = "MATERIAL - Distribuição total";

export const ANNUAL_TABLE_GROUPS = [
  { title: "PÚBLICO", rows: [["AUDIENCE - Geral", "Público total"], ["AUDIENCE - PALESTRAS", "Público em palestras"], ["AUDIENCE - ACOES", "Público em ações"]] },
  { title: "PALESTRAS", rows: [["LECTURES - Geral", "Total de palestras"], ["ACTION - Empresa", "Empresa"], ["ACTION - Escola", "Escola"], ["ACTION - Universidade", "Universidade"]] },
  { title: "AÇÕES", rows: [["STREET_ACTIONS - Geral", "Total de ações"], ["ACTION - Bares", "Bares/Restaurantes"], ["ACTION - Pedágio", "Pedágio"], ["ACTION - Praças Esportivas", "Praças Esportivas"], ["ACTION - Praia", "Praia"], ["ACTION - Eventos", "Eventos"], ["ACTION - Shopping", "Shopping/Centros Comerciais"], ["ACTION - Praças/Parques Públicos", "Praças/Parques Públicos"], ["ACTION - Pontos turísticos", "Pontos Turísticos"]] },
  { title: "MATERIAIS DE DISTRIBUIÇÃO", rows: [[ANNUAL_DISTRIBUTION_TOTAL_KEY, "Total de materiais de distribuição"], ["MATERIAL - Soprinho", "Revistinha Soprinho"], ["MATERIAL - Kit com 7 Revistinhas", "Kit com 7 Revistinhas"], ["MATERIAL - Ventarola Futebol", "Ventarola Futebol"]] },
];

export function withAnnualDistributionTotal(values = {}) {
  return {
    ...values,
    [ANNUAL_DISTRIBUTION_TOTAL_KEY]: ["MATERIAL - Soprinho", "MATERIAL - Kit com 7 Revistinhas", "MATERIAL - Ventarola Futebol"]
      .reduce((total, key) => total + Number(values[key] || 0), 0),
  };
}

export const ANNUAL_DISTRIBUTION_TOTAL_KEY = "MATERIAL - Distribuição total";

export const ANNUAL_TABLE_GROUPS = [
  { title: "Público", rows: [["AUDIENCE - Geral", "Público total"], ["AUDIENCE - PALESTRAS", "Público em palestras"], ["AUDIENCE - ACOES", "Público em ações"]] },
  { title: "Palestras total", rows: [["LECTURES - Geral", "Palestras total"], ["ACTION - Empresa", "Empresa"], ["ACTION - Escola", "Escola"], ["ACTION - Universidade", "Universidade"]] },
  { title: "Total de ações", rows: [["STREET_ACTIONS - Geral", "Total de ações"], ["ACTION - Bares", "Bares/Restaurantes"], ["ACTION - Pedágio", "Pedágio"], ["ACTION - Praças Esportivas", "Praças Esportivas"], ["ACTION - Praia", "Praia"], ["ACTION - Eventos", "Eventos"], ["ACTION - Shopping", "Shopping/Centros Comerciais"], ["ACTION - Praças/Parques Públicos", "Praças/Parques Públicos"], ["ACTION - Pontos turísticos", "Pontos Turísticos"]] },
  { title: "Materiais de distribuição total", rows: [[ANNUAL_DISTRIBUTION_TOTAL_KEY, "Materiais de distribuição total"], ["MATERIAL - Soprinho", "Revistinha Soprinho"], ["MATERIAL - Kit com 7 Revistinhas", "KIT COM 7 REVISTINHAS"], ["MATERIAL - Ventarola Futebol", "VENTAROLA FUTEBOL"]] },
];

export function withAnnualDistributionTotal(values = {}) {
  return {
    ...values,
    [ANNUAL_DISTRIBUTION_TOTAL_KEY]: ["MATERIAL - Soprinho", "MATERIAL - Kit com 7 Revistinhas", "MATERIAL - Ventarola Futebol"]
      .reduce((total, key) => total + Number(values[key] || 0), 0),
  };
}

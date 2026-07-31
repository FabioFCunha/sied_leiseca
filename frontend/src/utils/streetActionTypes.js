export const STREET_ACTION_TYPE_OPTIONS = [
  "Bares",
  "Pedágio",
  "Praças Esportivas",
  "Praia",
  "Eventos",
  "Shopping/Centro Comerciais",
  "Praças/Parques Públicos",
  "Pontos turísticos",
  "Ação conjunta com a fiscalização",
];

export const streetActionTypeLabel = (value) => {
  if (value === "Bares") return "Bares/Restaurantes";
  if (value === "Pontos turísticos") return "Pontos Turísticos";
  return value;
};

export const defaultGoalRows = [
  {
    key: "approach",
    label: "1 - ABORDADOS",
    section: true,
    average: 149478,
    target: 160000,
    children: [
      { key: "approached_lectures", label: "1.1 - ABORDADOS PALESTRAS", average: 29483, target: 40000 },
      { key: "approached_actions", label: "1.2 - ABORDADOS AÇÕES", average: 120491, target: 120000 },
    ],
  },
  {
    key: "lectures",
    label: "2 - PALESTRAS",
    section: true,
    average: 305,
    target: 320,
    children: [
      { key: "schools", label: "2.1 - ESCOLAS", average: 176, target: 220 },
      { key: "universities", label: "2.2 - UNIVERSIDADES", average: 5, target: 5 },
      { key: "companies", label: "2.3 - EMPRESAS", average: 124, target: 95 },
    ],
  },
  {
    key: "educational_actions",
    label: "3 - AÇÕES",
    section: true,
    average: 1062,
    target: 1000,
    children: [
      { key: "bars", label: "3.1 - BAR/RESTAURANTE", average: 126, target: 100 },
      { key: "tolls", label: "3.2 - PEDÁGIO", average: 6, target: 10 },
      { key: "sports", label: "3.3 - PRAÇA ESPORTIVA", average: 23, target: 20 },
      { key: "beach", label: "3.4 - PRAIA", average: 34, target: 50 },
      { key: "events", label: "3.5 - EVENTO", average: 127, target: 120 },
      { key: "shopping", label: "3.6 - SHOPPING", average: 15, target: 20 },
      { key: "social_actions", label: "3.7 - AÇÃO SOCIAL", average: 56, target: 50 },
      { key: "other_actions", label: "3.8 - OUTROS", average: 675, target: 630 },
    ],
  },
  {
    key: "publicity_materials",
    label: "4 - MATERIAIS DE DIVULGAÇÃO",
    section: true,
    average: 1199652,
    target: 200000,
    children: [
      { key: "distributed_certificates", label: "4.1 - CERTIFICADOS ENTREGUES", average: 3107, target: 5000 },
      { key: "gibis", label: '4.2 - KIT "Escolinha Nota 10"', average: 11539, target: 25000 },
    ],
  },
];

export function flattenGoalRows(rows = defaultGoalRows) {
  return rows.flatMap((row) => [row, ...(row.children || [])]);
}

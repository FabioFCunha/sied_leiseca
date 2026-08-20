import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

function loadImageAsBase64(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      resolve(canvas.toDataURL("image/png"));
    };
    img.onerror = reject;
    img.src = url;
  });
}

const NAVY = [10, 30, 68];
const NAVY_LIGHT = [20, 55, 110];
const GOLD = [196, 145, 33];
const GOLD_SOFT = [245, 222, 179];
const RED_SOFT = [255, 236, 236];
const RED_TEXT = [165, 28, 48];
const WHITE = [255, 255, 255];
const GRAY_900 = [28, 35, 49];
const GRAY_600 = [98, 108, 125];
const GRAY_300 = [208, 216, 228];
const GRAY_100 = [244, 247, 251];
const MARGIN_L = 14;
const MARGIN_R = 14;

const integer = (value) =>
  Number(value || 0).toLocaleString("pt-BR", {
    maximumFractionDigits: 0,
  });

const percentage = (value) => {
  if (value === null || value === undefined) {
    return "-";
  }

  return `${Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
};

const formatDate = (isoStr) => {
  if (!isoStr) {
    return "-";
  }

  const parts = String(isoStr).split("-");
  if (parts.length !== 3) {
    return isoStr;
  }

  return `${parts[2]}/${parts[1]}/${parts[0]}`;
};

function buildTerritoryRows(territorial) {
  const rows = [];
  const regions = territorial?.regions || [];
  const metropolitanRegion = regions.find(
    (region) => region.region_code === "METROPOLITANA"
  );
  const interiorRegions = regions.filter(
    (region) => region.region_code !== "METROPOLITANA"
  );

  if (metropolitanRegion) {
    const titleRow = [
      "REGIÃO METROPOLITANA",
      "",
      "",
      "",
      "",
      "",
    ];
    titleRow._type = "main-region";
    rows.push(titleRow);

    for (const item of metropolitanRegion.municipalities || []) {
      const isHigh =
        Number(item.metrics?.alcohol_percentage || 0) >= 25;
      const row = [
        `${item.municipality}`,
        integer(item.metrics?.approach),
        integer(item.metrics?.fined),
        integer(item.metrics?.alcohol_cases),
        percentage(item.metrics?.alcohol_percentage),
        integer(item.metrics?.operations),
      ];
      row._type = isHigh ? "highlight" : "municipality";
      rows.push(row);
    }

    const subtotalRow = [
      "Subtotal Região Metropolitana",
      integer(metropolitanRegion.metrics?.approach),
      integer(metropolitanRegion.metrics?.fined),
      integer(metropolitanRegion.metrics?.alcohol_cases),
      percentage(metropolitanRegion.metrics?.alcohol_percentage),
      integer(metropolitanRegion.metrics?.operations),
    ];
    subtotalRow._type = "subtotal";
    rows.push(subtotalRow);
  }

  if (interiorRegions.length > 0) {
    const interiorRow = [
      "INTERIOR",
      "",
      "",
      "",
      "",
      "",
    ];
    interiorRow._type = "main-region";
    rows.push(interiorRow);
  }

  for (const region of interiorRegions) {
    const regionHeaderRow = [
      String(region.region || "").toUpperCase(),
      "",
      "",
      "",
      "",
      "",
    ];
    regionHeaderRow._type = "region-header";
    rows.push(regionHeaderRow);

    for (const item of region.municipalities || []) {
      const isHigh =
        Number(item.metrics?.alcohol_percentage || 0) >= 25;
      const row = [
        `${item.municipality}`,
        integer(item.metrics?.approach),
        integer(item.metrics?.fined),
        integer(item.metrics?.alcohol_cases),
        percentage(item.metrics?.alcohol_percentage),
        integer(item.metrics?.operations),
      ];
      row._type = isHigh ? "highlight" : "municipality";
      rows.push(row);
    }

    const subtotalRow = [
      `Subtotal ${region.region}`,
      integer(region.metrics?.approach),
      integer(region.metrics?.fined),
      integer(region.metrics?.alcohol_cases),
      percentage(region.metrics?.alcohol_percentage),
      integer(region.metrics?.operations),
    ];
    subtotalRow._type = "subtotal";
    rows.push(subtotalRow);
  }

  return rows;
}

export async function generateInspectionTerritorialPdf({
  territorial,
  filters,
  issuedAt,
  logoUrl,
  openInNewTab = true,
}) {
  if (!territorial || !territorial.summary) {
    throw new Error(
      "Dados territoriais incompletos para gerar o PDF."
    );
  }

  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.width;
  const pageHeight = doc.internal.pageSize.height;
  const contentWidth =
    pageWidth - MARGIN_L - MARGIN_R;

  let logoBase64 = null;
  try {
    logoBase64 = await loadImageAsBase64(logoUrl);
  } catch (_) {}

  const drawRule = (y, color = GRAY_300, thickness = 0.3) => {
    doc.setDrawColor(...color);
    doc.setLineWidth(thickness);
    doc.line(MARGIN_L, y, pageWidth - MARGIN_R, y);
  };

  const ensureSpace = (needed, currentY) => {
    if (currentY > pageHeight - needed - 14) {
      doc.addPage();
      return 16;
    }
    return currentY;
  };

  const addFooter = () => {
    const totalPages = doc.internal.getNumberOfPages();
    for (let page = 1; page <= totalPages; page += 1) {
      doc.setPage(page);
      drawRule(pageHeight - 12);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(6.5);
      doc.setTextColor(...GRAY_600);
      doc.text(
        "SIED · Fiscalização · Análise Territorial",
        MARGIN_L,
        pageHeight - 8
      );
      doc.text(
        `${page} / ${totalPages}`,
        pageWidth - MARGIN_R,
        pageHeight - 8,
        { align: "right" }
      );
    }
  };

  const summary = territorial.summary || {};
  const regions = territorial.regions || [];
  const metropolitanRegion = regions.find(
    (region) => region.region_code === "METROPOLITANA"
  );
  const territoryRows = buildTerritoryRows(territorial);
  const highlighted = territorial.highlighted_operations || [];
  const unclassified = territorial.unclassified || [];
  const issued = issuedAt instanceof Date ? issuedAt : new Date();

  let y = 0;

  doc.setFillColor(...NAVY);
  doc.rect(0, 0, pageWidth, 22, "F");
  doc.setFillColor(...GOLD);
  doc.rect(0, 22, pageWidth, 0.8, "F");

  if (logoBase64) {
    const logoH = 14;
    const logoW = logoH * 3.3;
    const logoX = (pageWidth - logoW) / 2;
    doc.addImage(
      logoBase64,
      "PNG",
      logoX,
      4,
      logoW,
      logoH
    );
  }

  y = 31;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor(...NAVY);
  doc.text(
    "ANÁLISE TERRITORIAL DA FISCALIZAÇÃO",
    pageWidth / 2,
    y,
    { align: "center" }
  );
  y += 5.5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(...GRAY_600);
  doc.text(
    "Distribuição das ações de fiscalização por região e município",
    pageWidth / 2,
    y,
    { align: "center" }
  );
  y += 7;

  autoTable(doc, {
    startY: y,
    theme: "plain",
    body: [
      ["Período", `${formatDate(filters?.date_from)} a ${formatDate(filters?.date_to)}`],
      ["Emissão", issued.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })],
      ["Fonte", "HORUS / SIED"],
    ],
    tableWidth: contentWidth,
    margin: { left: MARGIN_L, right: MARGIN_R },
    styles: {
      fontSize: 8.4,
      cellPadding: { top: 2.4, bottom: 2.4, left: 4, right: 4 },
      textColor: GRAY_900,
    },
    alternateRowStyles: {
      fillColor: GRAY_100,
    },
    columnStyles: {
      0: {
        fontStyle: "bold",
        textColor: NAVY_LIGHT,
        cellWidth: 34,
      },
    },
  });
  y = doc.lastAutoTable.finalY + 8;

  autoTable(doc, {
    startY: y,
    head: [[
      "Indicador",
      "Valor",
    ]],
    body: [
      ["Abordados", integer(summary.approach)],
      ["Multados", integer(summary.fined)],
      ["Alcoolemia", integer(summary.alcohol_cases)],
      ["Percentual", percentage(summary.alcohol_percentage)],
      ["Fiscalizações", integer(summary.classified_operations)],
      ["Recusas", integer(summary.refusal)],
    ],
    theme: "grid",
    margin: { left: MARGIN_L, right: MARGIN_R },
    tableWidth: contentWidth,
    headStyles: {
      fillColor: NAVY,
      textColor: WHITE,
      fontStyle: "bold",
      fontSize: 8.5,
    },
    styles: {
      fontSize: 8.5,
      cellPadding: 2.6,
      textColor: GRAY_900,
    },
    alternateRowStyles: {
      fillColor: GRAY_100,
    },
    columnStyles: {
      1: {
        halign: "right",
        fontStyle: "bold",
        cellWidth: 34,
      },
    },
  });
  y = doc.lastAutoTable.finalY + 8;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(...NAVY);
  doc.text("FISCALIZAÇÃO POR TERRITÓRIO", MARGIN_L, y);
  y += 2;
  drawRule(y, NAVY_LIGHT, 0.45);
  y += 4;

  autoTable(doc, {
    startY: y,
    head: [[
      "Região / Município",
      "Abordados",
      "Multados",
      "Alcoolemia",
      "% Alc.",
      "Fiscalizações",
    ]],
    body: territoryRows,
    foot: [
      metropolitanRegion
        ? [
            "Total Região Metropolitana",
            integer(metropolitanRegion.metrics?.approach),
            integer(metropolitanRegion.metrics?.fined),
            integer(metropolitanRegion.metrics?.alcohol_cases),
            percentage(metropolitanRegion.metrics?.alcohol_percentage),
            integer(metropolitanRegion.metrics?.operations),
          ]
        : null,
      territorial.interior
        ? [
            "Total Interior",
            integer(territorial.interior.approach),
            integer(territorial.interior.fined),
            integer(territorial.interior.alcohol_cases),
            percentage(territorial.interior.alcohol_percentage),
            integer(territorial.interior.operations),
          ]
        : null,
      [
        "Total Geral",
        integer(summary.approach),
        integer(summary.fined),
        integer(summary.alcohol_cases),
        percentage(summary.alcohol_percentage),
        integer(summary.classified_operations),
      ],
    ].filter(Boolean),
    theme: "grid",
    margin: { left: MARGIN_L, right: MARGIN_R },
    tableWidth: contentWidth,
    headStyles: {
      fillColor: NAVY,
      textColor: WHITE,
      fontStyle: "bold",
      fontSize: 8,
      cellPadding: 2.4,
    },
    footStyles: {
      fillColor: NAVY,
      textColor: WHITE,
      fontStyle: "bold",
      fontSize: 8,
      cellPadding: 2.4,
    },
    styles: {
      fontSize: 7.8,
      cellPadding: 2.1,
      textColor: GRAY_900,
      overflow: "linebreak",
      valign: "middle",
    },
    alternateRowStyles: {
      fillColor: WHITE,
    },
    columnStyles: {
      0: { cellWidth: 62 },
      1: { halign: "right", cellWidth: 22 },
      2: { halign: "right", cellWidth: 22 },
      3: { halign: "right", cellWidth: 22 },
      4: { halign: "right", cellWidth: 20 },
      5: { halign: "right", cellWidth: 22 },
    },
    didParseCell: (hookData) => {
      const rowType = hookData.row.raw?._type;
      if (!rowType || hookData.section !== "body") {
        return;
      }

      if (rowType === "main-region") {
        hookData.cell.styles.fillColor = NAVY;
        hookData.cell.styles.textColor = GOLD;
        hookData.cell.styles.fontStyle = "bold";
        if (hookData.column.index > 0) {
          hookData.cell.text = [""];
        }
      }

      if (rowType === "region-header") {
        hookData.cell.styles.fillColor = GRAY_100;
        hookData.cell.styles.textColor = NAVY;
        hookData.cell.styles.fontStyle = "bold";
        if (hookData.column.index > 0) {
          hookData.cell.text = [""];
        }
      }

      if (rowType === "subtotal") {
        hookData.cell.styles.fillColor = [228, 235, 247];
        hookData.cell.styles.fontStyle = "bold";
      }

      if (rowType === "highlight") {
        hookData.cell.styles.fillColor = RED_SOFT;
        if (hookData.column.index === 4) {
          hookData.cell.styles.textColor = RED_TEXT;
          hookData.cell.styles.fontStyle = "bold";
        }
      }
    },
  });
  y = doc.lastAutoTable.finalY + 8;

  if (highlighted.length > 0) {
    y = ensureSpace(38, y);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(...RED_TEXT);
    doc.text(
      "FISCALIZAÇÕES COM ÍNDICE DE ALCOOLEMIA ≥ 25%",
      MARGIN_L,
      y
    );
    y += 2;
    drawRule(y, RED_TEXT, 0.35);
    y += 4;

    autoTable(doc, {
      startY: y,
      head: [[
        "Data",
        "Equipe",
        "Município",
        "Região",
        "Abordados",
        "Alcoolemia",
        "Percentual",
      ]],
      body: highlighted.map((item) => [
        formatDate(item.date),
        item.team || "-",
        item.municipality,
        item.region,
        integer(item.approach),
        integer(item.alcohol_cases),
        percentage(item.alcohol_percentage),
      ]),
      theme: "grid",
      margin: { left: MARGIN_L, right: MARGIN_R },
      tableWidth: contentWidth,
      headStyles: {
        fillColor: [123, 24, 24],
        textColor: WHITE,
        fontStyle: "bold",
        fontSize: 7.9,
      },
      styles: {
        fontSize: 7.7,
        cellPadding: 2.1,
        textColor: GRAY_900,
      },
      alternateRowStyles: {
        fillColor: [255, 246, 246],
      },
      columnStyles: {
        0: { cellWidth: 19 },
        1: { cellWidth: 15, halign: "center" },
        2: { cellWidth: 38 },
        3: { cellWidth: 33 },
        4: { cellWidth: 18, halign: "right" },
        5: { cellWidth: 18, halign: "right" },
        6: { cellWidth: 22, halign: "right", fontStyle: "bold" },
      },
    });
    y = doc.lastAutoTable.finalY + 8;
  }

  if (unclassified.length > 0) {
    y = ensureSpace(32, y);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(...GRAY_600);
    doc.text(
      "REGISTROS TERRITORIAIS NÃO CLASSIFICADOS",
      MARGIN_L,
      y
    );
    y += 2;
    drawRule(y);
    y += 4;

    autoTable(doc, {
      startY: y,
      head: [[
        "Município recebido",
        "Nome normalizado",
        "Fiscalizações",
        "Abordados",
      ]],
      body: unclassified.map((item) => [
        item.source_city || "(vazio)",
        item.normalized_city || "-",
        integer(item.operations),
        integer(item.approach),
      ]),
      theme: "grid",
      margin: { left: MARGIN_L, right: MARGIN_R },
      tableWidth: contentWidth,
      headStyles: {
        fillColor: [114, 124, 146],
        textColor: WHITE,
        fontStyle: "bold",
        fontSize: 7.9,
      },
      styles: {
        fontSize: 7.7,
        cellPadding: 2.1,
        textColor: GRAY_900,
      },
      alternateRowStyles: {
        fillColor: GRAY_100,
      },
      columnStyles: {
        0: { cellWidth: 58 },
        1: { cellWidth: 58 },
        2: { halign: "right", cellWidth: 28 },
        3: { halign: "right", cellWidth: 28 },
      },
    });
    y = doc.lastAutoTable.finalY + 8;
  }

  y = ensureSpace(34, y);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(...NAVY);
  doc.text("NOTA METODOLÓGICA", MARGIN_L, y);
  y += 2;
  drawRule(y, NAVY_LIGHT, 0.35);
  y += 5;

  const methodologyLines = [
    "Alcoolemia: soma de recusas + infrações administrativas Art. 165 + crimes Art. 306 + outros meios/sinais notórios.",
    "Percentual: total de casos de alcoolemia dividido pelo total de abordados.",
    "Art. 307: contabilizado separadamente.",
    "Fonte territorial: município registrado na operação e classificado pela tabela oficial InspectionMunicipality → InspectionRegion.",
    "Fonte operacional: HORUS / SIED.",
  ];

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.2);
  doc.setTextColor(...GRAY_900);
  for (const line of methodologyLines) {
    const wrapped = doc.splitTextToSize(
      `• ${line}`,
      contentWidth
    );
    doc.text(wrapped, MARGIN_L, y);
    y += wrapped.length * 4.1;
  }

  addFooter();

  const fileName =
    "analise-territorial-fiscalizacao.pdf";

  if (openInNewTab) {
    window.open(doc.output("bloburl"), "_blank");
    return;
  }

  doc.save(fileName);
}

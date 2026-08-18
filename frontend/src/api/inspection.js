
import { api } from "./client.js";

function buildQuery(params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    searchParams.set(key, String(value));
  });

  return searchParams.toString();
}

export function listInspectionReports(params = {}) {
  const query = buildQuery(params);
  return api(`/inspection/reports/${query ? `?${query}` : ""}`);
}

export function getInspectionReport(id) {
  return api(`/inspection/reports/${id}/`);
}

export function includeInspectionReportInStatistics(id, classification) {
  return api(`/inspection/reports/${id}/include-in-statistics/`, {
    method: "POST",
    body: JSON.stringify({
      classification,
    }),
  });
}

export function excludeInspectionReportFromStatistics(id, reason) {
  return api(`/inspection/reports/${id}/exclude-from-statistics/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function listInspectionReportsByPageUrl(pageUrl) {
  if (!pageUrl) {
    return listInspectionReports();
  }

  try {
    const parsed = new URL(pageUrl);
    const apiPath = `${parsed.pathname}${parsed.search}`;
    const normalizedPath = apiPath.startsWith("/api")
      ? apiPath.slice(4)
      : apiPath;

    return api(normalizedPath);
  } catch {
    return api(pageUrl);
  }
}

export function getInspectionTerritorialStatistics(params = {}) {
  const query = buildQuery(params);

  return api(
    `/inspection/statistics/territorial/${query ? `?${query}` : ""}`
  );
}
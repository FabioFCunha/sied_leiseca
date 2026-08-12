import { api } from "./client.js";

function buildQuery(params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    searchParams.set(key, String(value));
  });

  return searchParams.toString();
}

export function getInspectionStatisticsDashboard(params = {}) {
  const query = buildQuery(params);
  return api(`/inspection/statistics/dashboard/${query ? `?${query}` : ""}`);
}

const API_URL = import.meta.env?.VITE_API_URL || "/api";
const DEFAULT_TIMEOUT_MS = Number(import.meta.env?.VITE_API_TIMEOUT_MS || 12000);

let isRefreshing = false;
let refreshQueue = [];

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("refreshToken");
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    localStorage.setItem("accessToken", data.access);
    if (data.refresh) localStorage.setItem("refreshToken", data.refresh);
    return data.access;
  } catch {
    return null;
  }
}

export function getToken() {
  return localStorage.getItem("accessToken");
}

function formatApiError(data) {
  if (!data || data instanceof Blob) {
    return "Nao foi possivel concluir a operacao.";
  }
  if (data.detail) {
    if (typeof data.detail === "string" && data.detail.includes("matches the given query")) {
      return "O registro solicitado não foi encontrado ou já foi excluído.";
    }
    return data.detail;
  }
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return data.non_field_errors[0];
  }
  const fieldLabels = {
    type_action: "Tipo da ação",
    requester_entity_kind: "Tipo da entidade",
    requester_entity_nature: "Natureza da entidade",
    age_range: "Faixa etária",
    agreement_indicator: "Indicador do convênio",
    approach: "Público estimado",
    approached_actions: "Número de abordagens",
    approached_lectures: "Abordados em palestras",
  };
  const prettifyField = (field) => fieldLabels[field] || String(field || "").replaceAll("_", " ");
  const isNumericKey = (value) => /^\d+$/.test(String(value || ""));
  const collectMessages = (value, path = []) => {
    if (value === null || value === undefined || value === "") return [];
    if (typeof value === "string" || typeof value === "number") {
      const actionPathIndex = path.findIndex((segment) => segment === "actions");
      if (actionPathIndex >= 0) {
        const rawIndex = path[actionPathIndex + 1];
        const actionNumber = isNumericKey(rawIndex) ? Number(rawIndex) + 1 : null;
        if (actionNumber !== null) {
          return [`Ação ${String(actionNumber).padStart(2, "0")}: ${value}`];
        }
      }
      const lastPath = path[path.length - 1];
      if (!lastPath || lastPath === "non_field_errors") {
        return [String(value)];
      }
      return [`${prettifyField(lastPath)}: ${value}`];
    }
    if (Array.isArray(value)) {
      if (value.every((item) => typeof item === "string" || typeof item === "number")) {
        return value.flatMap((item) => collectMessages(item, path));
      }
      return value.flatMap((item, index) => {
        const nextPath = path[path.length - 1] === "actions" ? [...path, String(index)] : path;
        return collectMessages(item, nextPath);
      });
    }
    if (typeof value === "object") {
      return Object.entries(value).flatMap(([field, nestedValue]) =>
        collectMessages(nestedValue, [...path, field])
      );
    }
    return [];
  };
  if (typeof data === "object") {
    const fieldMessages = collectMessages(data);
    if (fieldMessages.length) {
      return [...new Set(fieldMessages)].join("\n");
    }
  }
  return "Nao foi possivel concluir a operacao.";
}

export { formatApiError };

async function formatResponseError(data, status) {
  if (data instanceof Blob) {
    const text = await data.text();
    if (text.includes("no such table")) {
      return "Banco local desatualizado. Rode as migracoes do backend e tente novamente.";
    }
    if (text.includes("UNIQUE constraint") || text.includes("duplicate key")) {
      return "Esta equipe ja esta escalada para este dia.";
    }
    return `Nao foi possivel concluir a operacao. Erro ${status}.`;
  }
  return formatApiError(data);
}

export async function api(path, options = {}) {
  const { redirectOnUnauthorized = true, timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options;
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response;
  const controller = fetchOptions.signal ? null : new AbortController();
  const timeoutId = controller && timeoutMs > 0
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...fetchOptions,
      headers,
      signal: fetchOptions.signal || controller?.signal,
    });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("A API demorou muito para responder (pode estar iniciando). Tente novamente em alguns segundos.");
    }
    throw new Error("Não foi possível conectar à API. Verifique sua conexão ou se a API está online.");
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  }
  if (response.status === 204) {
    return null;
  }
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.blob();
  if (!response.ok) {
    if (response.status === 401 && redirectOnUnauthorized) {
      // Try token refresh before logging out
      if (!isRefreshing) {
        isRefreshing = true;
        const newToken = await refreshAccessToken();
        isRefreshing = false;

        if (newToken) {
          // Retry the original request with new token
          const retryHeaders = { ...Object.fromEntries(headers.entries()), Authorization: `Bearer ${newToken}` };
          const retryRes = await fetch(`${API_URL}${path}`, { ...fetchOptions, headers: retryHeaders, signal: fetchOptions.signal || controller?.signal });
          if (retryRes.ok || retryRes.status !== 401) {
            // Process the retry response same as success
            const ct = retryRes.headers.get("content-type") || "";
            if (retryRes.status === 204) return null;
            return ct.includes("json") ? retryRes.json() : retryRes.text();
          }
        }
      }

      // Refresh failed - logout
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
      window.location.href = "/login";
      throw new Error("Sessão expirada");
    }
    throw new Error(await formatResponseError(data, response.status));
  }
  return data;
}

export function downloadUrl(path) {
  return `${API_URL}${path}`;
}

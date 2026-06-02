const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export function getToken() {
  return localStorage.getItem("accessToken");
}

export async function api(path, options = {}) {
  const { redirectOnUnauthorized = true, ...fetchOptions } = options;
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...fetchOptions, headers });
  if (response.status === 204) {
    return null;
  }
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.blob();
  if (!response.ok) {
    if (response.status === 401 && redirectOnUnauthorized) {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    const message = data?.detail || data?.non_field_errors?.[0] || "Não foi possível concluir a operação.";
    throw new Error(message);
  }
  return data;
}

export function downloadUrl(path) {
  return `${API_URL}${path}`;
}

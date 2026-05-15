import type { AnalysisData, ApiEnvelope, ExtractionData, ProjectSummary, TaskStatus, VisualizationData } from "./types";

const TOKEN_KEY = "structure-agent-token";
const API_BASE_KEY = "structure-agent-api-base";

export const DEFAULT_API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setStoredToken(token: string) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getStoredApiBase() {
  return localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE;
}

export function setStoredApiBase(base: string) {
  localStorage.setItem(API_BASE_KEY, trimTrailingSlash(base));
}

export function trimTrailingSlash(value: string) {
  return value.trim().replace(/\/+$/, "");
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as T;
  }
}

async function request<T>(
  apiBase: string,
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${trimTrailingSlash(apiBase)}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  const payload = await readJson<ApiEnvelope<T> | T>(response);
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? String((payload as { detail?: unknown }).detail)
        : response.statusText;
    throw new ApiError(detail || "Request failed", response.status);
  }

  return payload as T;
}

function parseMaybeJson<T>(value: unknown): T {
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as T;
    } catch {
      return value as T;
    }
  }
  return value as T;
}

export async function health(apiBase: string) {
  return request<string>(apiBase, "/health", "", { method: "GET" });
}

export async function signup(apiBase: string, form: { name: string; email: string; password: string }) {
  return request<ApiEnvelope<string>>(apiBase, "/api/auth/signup", "", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
}

export async function login(apiBase: string, form: { email: string; password: string }) {
  const payload = await request<ApiEnvelope<unknown>>(apiBase, "/api/auth/login", "", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!payload.access_token) {
    throw new ApiError("Login completed without an access token", 500);
  }
  return payload.access_token;
}

export async function getProjects(apiBase: string, token: string) {
  const payload = await request<ApiEnvelope<unknown[]>>(apiBase, "/api/crud/get_all_projects", token);
  const rows = Array.isArray(payload.data) ? payload.data : [];
  return rows.map((row): ProjectSummary => {
    if (Array.isArray(row)) {
      return { id: String(row[0]), filename: String(row[1] ?? "Untitled project") };
    }
    const item = row as Record<string, unknown>;
    return {
      id: String(item.id ?? item[0] ?? ""),
      filename: String(item.filename ?? item[1] ?? "Untitled project"),
    };
  });
}

export async function getProject(apiBase: string, token: string, projectId: string) {
  const payload = await request<ApiEnvelope<unknown>>(
    apiBase,
    `/api/crud/get_project?project_id=${encodeURIComponent(projectId)}`,
    token,
  );
  return parseMaybeJson<ExtractionData>(payload.data);
}

export async function getVisualization(apiBase: string, token: string, projectId: string) {
  const payload = await request<ApiEnvelope<unknown>>(
    apiBase,
    `/api/crud/get_project_visualization?project_id=${encodeURIComponent(projectId)}`,
    token,
  );
  return parseMaybeJson<VisualizationData>(payload.data);
}

export async function deleteProject(apiBase: string, token: string, projectId: string) {
  return request<ApiEnvelope<string>>(
    apiBase,
    `/api/crud/delete_project?project_id=${encodeURIComponent(projectId)}`,
    token,
    { method: "DELETE" },
  );
}

export async function startExtraction(apiBase: string, token: string, file: File) {
  const form = new FormData();
  form.append("structure_plan", file);
  return request<ApiEnvelope<string> & { project_id?: string; task_id?: string }>(apiBase, "/api/start_agent", token, {
    method: "POST",
    body: form,
  });
}

export async function checkStatus(apiBase: string, taskId: string) {
  return request<TaskStatus>(
    apiBase,
    `/api/check_status?task_id=${encodeURIComponent(taskId)}`,
    "",
  );
}

export async function getAnalysis(apiBase: string, token: string, projectId: string) {
  const payload = await request<ApiEnvelope<unknown>>(
    apiBase,
    `/api/analysis/get_final_analysis?project_id=${encodeURIComponent(projectId)}`,
    token,
  );
  return parseMaybeJson<AnalysisData>(payload.data);
}

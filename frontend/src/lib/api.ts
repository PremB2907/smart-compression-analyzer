const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("sa_token");
}

export function setToken(token: string) {
  localStorage.setItem("sa_token", token);
}

export function clearToken() {
  localStorage.removeItem("sa_token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    ...(options.headers || {}),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export async function register(email: string, password: string, fullName?: string) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export async function getDashboard() {
  return apiFetch<{
    cards: Record<string, number | null>;
    charts: Record<string, Record<string, number | null>>;
    leaderboard: { format: string; score: number }[];
    formulas: Record<string, string>;
  }>("/dashboard/overview");
}

export async function uploadFiles(files: FileList | File[]) {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  const token = getToken();
  const res = await fetch(`${API_URL}/uploads`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function getAnalysis(uploadId: number) {
  return apiFetch(`/uploads/${uploadId}`);
}

export async function getTaskStatus(uploadId: number) {
  return apiFetch(`/uploads/${uploadId}/task`);
}

export async function startBenchmark() {
  return apiFetch("/benchmark/run", { method: "POST" });
}

export async function getBenchmark(id: number) {
  return apiFetch(`/benchmark/${id}`);
}

export async function aiPreview(uploadId: number) {
  return apiFetch(`/uploads/${uploadId}/ai-preview`, { method: "POST" });
}

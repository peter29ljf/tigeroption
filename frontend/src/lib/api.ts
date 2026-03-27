const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function wsUrl(path: string): string {
  return `${WS_BASE}${path}`;
}

export async function apiFetch<T = unknown>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

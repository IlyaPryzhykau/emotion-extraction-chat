// Thin API client. Types mirror the backend Pydantic schemas (app/api/schemas.py).
// All requests send the session cookie (credentials: "include").

export type ConversationStatus = "active" | "analyzed";
export type MessageRole = "user" | "assistant";
export type Intensity = "low" | "medium" | "high";
export type EmotionLabel =
  | "sadness"
  | "anxiety"
  | "anger"
  | "frustration"
  | "fear"
  | "guilt"
  | "shame"
  | "loneliness"
  | "disappointment"
  | "stress/overwhelm";

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ConversationListItem {
  id: string;
  status: ConversationStatus;
  started_at: string;
  ended_at: string | null;
  labels: EmotionLabel[];
}

export interface ConversationDetail {
  id: string;
  status: ConversationStatus;
  started_at: string;
  ended_at: string | null;
  messages: Message[];
}

export interface Emotion {
  id: string;
  label: EmotionLabel;
  intensity: Intensity;
  trigger: string;
  evidence: string;
  confidence: number;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((body) => body.detail)
      .catch(() => null);
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  signup: (email: string, password: string) =>
    request<User>("/api/auth/signup", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<User>("/api/auth/me"),

  createConversation: () => request<ConversationListItem>("/api/conversations", { method: "POST" }),
  listConversations: () => request<ConversationListItem[]>("/api/conversations"),
  getConversation: (id: string) => request<ConversationDetail>(`/api/conversations/${id}`),
  analyze: (id: string) => request<Emotion[]>(`/api/conversations/${id}/analyze`, { method: "POST" }),
  getReport: (id: string) => request<Emotion[]>(`/api/conversations/${id}/report`),
};

export interface StreamHandlers {
  onDelta: (text: string) => void;
  onDone: (messageId: string) => void;
  onError: (message: string) => void;
}

/**
 * Post a user message and consume the assistant reply as Server-Sent Events.
 *
 * Native EventSource can't POST a body, so we read the streamed response with a
 * fetch ReadableStream and parse the `data: {json}` lines ourselves.
 */
export async function streamMessage(
  conversationId: string,
  content: string,
  handlers: StreamHandlers,
): Promise<void> {
  const res = await fetch(`/api/conversations/${conversationId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!res.ok || !res.body) {
    const detail = await res
      .json()
      .then((body) => body.detail)
      .catch(() => null);
    handlers.onError(typeof detail === "string" ? detail : "Failed to send message");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? ""; // keep any incomplete trailing event
    for (const event of events) {
      const line = event.trim();
      if (!line.startsWith("data:")) continue;
      const payload = JSON.parse(line.slice("data:".length).trim());
      if (typeof payload.delta === "string") handlers.onDelta(payload.delta);
      else if (payload.done) handlers.onDone(payload.message_id);
      else if (payload.error) handlers.onError(payload.error);
    }
  }
}

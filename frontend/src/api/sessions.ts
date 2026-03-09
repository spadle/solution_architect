import { api } from "./client";
import type { Session, Mode } from "../types/session";
import type { ConversationResponse, Message } from "../types/message";
import type { DiagramState } from "../types/diagram";

export async function getModes(): Promise<Mode[]> {
  return api.get<Mode[]>("/modes");
}

export async function createSession(
  mode_id: string,
  title?: string
): Promise<Session> {
  return api.post<Session>("/sessions", { mode_id, title });
}

export async function getSessions(): Promise<{ sessions: Session[] }> {
  return api.get<{ sessions: Session[] }>("/sessions");
}

export async function getSession(id: string): Promise<Session> {
  return api.get<Session>(`/sessions/${id}`);
}

export async function updateSession(
  id: string,
  data: { title?: string; status?: string }
): Promise<Session> {
  return api.patch<Session>(`/sessions/${id}`, data);
}

export async function deleteSession(id: string): Promise<void> {
  return api.delete<void>(`/sessions/${id}`);
}

export async function startSession(
  id: string
): Promise<ConversationResponse> {
  return api.post<ConversationResponse>(`/sessions/${id}/start`);
}

export async function resumeSession(
  id: string
): Promise<ConversationResponse> {
  return api.post<ConversationResponse>(`/sessions/${id}/resume`);
}

export async function sendMessage(
  sessionId: string,
  content: string
): Promise<ConversationResponse> {
  return api.post<ConversationResponse>(`/sessions/${sessionId}/messages`, {
    content,
  });
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  return api.get<Message[]>(`/sessions/${sessionId}/messages`);
}

export async function getDiagram(sessionId: string): Promise<DiagramState> {
  return api.get<DiagramState>(`/sessions/${sessionId}/diagram`);
}

export async function getMermaid(
  sessionId: string
): Promise<{ syntax: string }> {
  return api.get<{ syntax: string }>(`/sessions/${sessionId}/diagram/mermaid`);
}

export async function exportDiagram(
  sessionId: string,
  format: string
): Promise<unknown> {
  return api.post(`/sessions/${sessionId}/diagram/export`, { format });
}

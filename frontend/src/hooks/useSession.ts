import { useCallback } from "react";
import {
  createSession,
  startSession,
  sendMessage,
  getMessages,
  getDiagram,
  getMermaid,
} from "../api/sessions";
import { useSessionStore } from "../stores/sessionStore";
import { useDiagramStore } from "../stores/diagramStore";

export function useSession() {
  const store = useSessionStore();
  const diagramStore = useDiagramStore();

  const create = useCallback(
    async (modeId: string, title?: string) => {
      store.setLoading(true);
      store.setError(null);
      try {
        const session = await createSession(modeId, title);
        store.setSession(session);

        // Start the session (triggers first AI message)
        const response = await startSession(session.id);
        store.addMessage(response.message);
        store.setCurrentQuestion(response.question);

        // Load initial diagram
        const diagram = await getDiagram(session.id);
        diagramStore.setFullState(diagram.nodes, diagram.edges);

        return session;
      } catch (err) {
        store.setError(
          err instanceof Error ? err.message : "Failed to create session"
        );
        return null;
      } finally {
        store.setLoading(false);
      }
    },
    [store, diagramStore]
  );

  const send = useCallback(
    async (content: string) => {
      if (!store.session) return;

      // Add user message optimistically
      store.addMessage({
        id: `temp-${Date.now()}`,
        session_id: store.session.id,
        sequence: store.messages.length + 1,
        role: "user",
        content,
        structured_data: null,
        node_id: null,
        created_at: new Date().toISOString(),
      });

      store.setLoading(true);
      store.setError(null);
      store.setCurrentQuestion(null);

      try {
        const response = await sendMessage(store.session.id, content);
        store.addMessage(response.message);
        store.setCurrentQuestion(response.question);

        // Refresh diagram (WebSocket also sends updates)
        const diagram = await getDiagram(store.session.id);
        diagramStore.setFullState(diagram.nodes, diagram.edges);

        // Also refresh mermaid syntax
        const mermaid = await getMermaid(store.session.id);
        diagramStore.setMermaidSyntax(mermaid.syntax);
      } catch (err) {
        store.setError(
          err instanceof Error ? err.message : "Failed to send message"
        );
      } finally {
        store.setLoading(false);
      }
    },
    [store, diagramStore]
  );

  const loadSession = useCallback(
    async (sessionId: string) => {
      store.setLoading(true);
      try {
        const [messages, diagram, mermaid] = await Promise.all([
          getMessages(sessionId),
          getDiagram(sessionId),
          getMermaid(sessionId),
        ]);
        store.setMessages(messages);
        diagramStore.setFullState(diagram.nodes, diagram.edges);
        diagramStore.setMermaidSyntax(mermaid.syntax);

        // Find last question
        const lastAssistant = [...messages]
          .reverse()
          .find((m) => m.role === "assistant" && m.structured_data);
        if (lastAssistant?.structured_data) {
          store.setCurrentQuestion(
            lastAssistant.structured_data as import("../types/message").QuestionData
          );
        }
      } catch (err) {
        store.setError(
          err instanceof Error ? err.message : "Failed to load session"
        );
      } finally {
        store.setLoading(false);
      }
    },
    [store, diagramStore]
  );

  return { create, send, loadSession };
}

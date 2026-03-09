import { useEffect, useCallback } from "react";
import { useSessionStore } from "./stores/sessionStore";
import { useDiagramStore } from "./stores/diagramStore";
import { useSession } from "./hooks/useSession";
import { useWebSocket } from "./hooks/useWebSocket";
import { getModes, getSessions, deleteSession, exportDiagram, getSession } from "./api/sessions";
import { AppLayout } from "./components/layout/AppLayout";
import { Header } from "./components/layout/Header";
import { ChatPanel } from "./components/chat/ChatPanel";
import { DiagramPanel } from "./components/diagram/DiagramPanel";
import { ModeSelector } from "./components/session/ModeSelector";
import { SessionList } from "./components/session/SessionList";
import type { Mode, Session } from "./types/session";

export default function App() {
  const session = useSessionStore((s) => s.session);
  const modes = useSessionStore((s) => s.modes);
  const sessions = useSessionStore((s) => s.sessions);
  const isLoading = useSessionStore((s) => s.isLoading);
  const setSession = useSessionStore((s) => s.setSession);
  const setModes = useSessionStore((s) => s.setModes);
  const setSessions = useSessionStore((s) => s.setSessions);
  const clearSession = useSessionStore((s) => s.clear);
  const clearDiagram = useDiagramStore((s) => s.clear);
  const { create, loadSession } = useSession();

  // Connect WebSocket when session is active
  useWebSocket(session?.id || null);

  // Load modes and sessions on mount
  useEffect(() => {
    getModes().then(setModes).catch(console.error);
    getSessions()
      .then((data) => setSessions(data.sessions))
      .catch(console.error);
  }, [setModes, setSessions]);

  const handleModeSelect = useCallback(
    async (mode: Mode) => {
      await create(mode.id, `${mode.name} Session`);
    },
    [create]
  );

  const handleSessionSelect = useCallback(
    async (s: Session) => {
      const full = await getSession(s.id);
      setSession(full);
      await loadSession(s.id);
    },
    [setSession, loadSession]
  );

  const handleSessionDelete = useCallback(
    async (id: string) => {
      await deleteSession(id);
      const data = await getSessions();
      setSessions(data.sessions);
    },
    [setSessions]
  );

  const handleBack = useCallback(() => {
    clearSession();
    clearDiagram();
    getSessions()
      .then((data) => setSessions(data.sessions))
      .catch(console.error);
  }, [clearSession, clearDiagram, setSessions]);

  const handleExport = useCallback(
    async (format: string) => {
      if (!session) return;
      const data = await exportDiagram(session.id, format);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${session.title}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    },
    [session]
  );

  // Show mode selector when no active session
  if (!session) {
    return (
      <div>
        <ModeSelector
          modes={modes}
          onSelect={handleModeSelect}
          loading={isLoading}
        />
        <div className="px-8 pb-8">
          <SessionList
            sessions={sessions}
            onSelect={handleSessionSelect}
            onDelete={handleSessionDelete}
          />
        </div>
      </div>
    );
  }

  // Show consultation workspace
  return (
    <AppLayout
      header={<Header onBack={handleBack} onExport={handleExport} />}
      chat={<ChatPanel />}
      diagram={<DiagramPanel />}
    />
  );
}

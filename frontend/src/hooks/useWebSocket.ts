import { useEffect, useRef } from "react";
import { WebSocketClient } from "../api/websocket";
import { useDiagramStore } from "../stores/diagramStore";
import { useSessionStore } from "../stores/sessionStore";

export function useWebSocket(sessionId: string | null) {
  const clientRef = useRef<WebSocketClient | null>(null);
  const handleEvent = useDiagramStore((s) => s.handleEvent);
  const setWsConnected = useSessionStore((s) => s.setWsConnected);

  useEffect(() => {
    if (!sessionId) return;

    const client = new WebSocketClient(
      sessionId,
      handleEvent,
      setWsConnected
    );
    client.connect();
    clientRef.current = client;

    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [sessionId, handleEvent, setWsConnected]);

  return clientRef;
}

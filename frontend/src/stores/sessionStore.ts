import { create } from "zustand";
import type { Session, Mode } from "../types/session";
import type { Message, QuestionData } from "../types/message";

interface SessionStore {
  // Current session
  session: Session | null;
  messages: Message[];
  currentQuestion: QuestionData | null;
  isLoading: boolean;
  error: string | null;

  // Session list
  sessions: Session[];
  modes: Mode[];

  // WebSocket
  wsConnected: boolean;

  // Actions
  setSession: (session: Session | null) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setCurrentQuestion: (question: QuestionData | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSessions: (sessions: Session[]) => void;
  setModes: (modes: Mode[]) => void;
  setWsConnected: (connected: boolean) => void;
  clear: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  session: null,
  messages: [],
  currentQuestion: null,
  isLoading: false,
  error: null,
  sessions: [],
  modes: [],
  wsConnected: false,

  setSession: (session) => set({ session }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  setCurrentQuestion: (question) => set({ currentQuestion: question }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setSessions: (sessions) => set({ sessions }),
  setModes: (modes) => set({ modes }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  clear: () =>
    set({
      session: null,
      messages: [],
      currentQuestion: null,
      isLoading: false,
      error: null,
    }),
}));

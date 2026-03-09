import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { useSessionStore } from "../../stores/sessionStore";
import { useSession } from "../../hooks/useSession";
import { MessageBubble } from "./MessageBubble";
import { ChoiceSelector } from "./ChoiceSelector";

export function ChatPanel() {
  const messages = useSessionStore((s) => s.messages);
  const currentQuestion = useSessionStore((s) => s.currentQuestion);
  const isLoading = useSessionStore((s) => s.isLoading);
  const error = useSessionStore((s) => s.error);
  const { send } = useSession();

  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    await send(text);
    inputRef.current?.focus();
  };

  const handleChoiceSelect = async (choice: string) => {
    if (isLoading) return;
    await send(choice);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
              <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Choice selector */}
      {currentQuestion && (
        <ChoiceSelector
          question={currentQuestion}
          onSelect={handleChoiceSelect}
          disabled={isLoading}
        />
      )}

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              currentQuestion?.question_type === "free_text"
                ? "Type your answer..."
                : "Type a message or select a choice above..."
            }
            className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2
                       text-sm focus:outline-none focus:ring-2 focus:ring-primary-500
                       focus:border-transparent placeholder:text-gray-400"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="btn-primary flex items-center gap-1"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

import { Clock, Trash2 } from "lucide-react";
import type { Session } from "../../types/session";

interface SessionListProps {
  sessions: Session[];
  onSelect: (session: Session) => void;
  onDelete: (sessionId: string) => void;
}

export function SessionList({ sessions, onSelect, onDelete }: SessionListProps) {
  if (sessions.length === 0) return null;

  return (
    <div className="mt-12 max-w-4xl mx-auto w-full">
      <h2 className="text-lg font-semibold text-gray-700 mb-4">
        Recent Sessions
      </h2>
      <div className="space-y-2">
        {sessions.map((session) => (
          <div
            key={session.id}
            className="card flex items-center gap-4 cursor-pointer hover:border-primary-300 transition-colors"
            onClick={() => onSelect(session)}
          >
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-900 truncate">
                {session.title}
              </h3>
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span className="capitalize">
                  {session.mode_id.replace(/_/g, " ")}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(session.updated_at).toLocaleDateString()}
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    session.status === "active"
                      ? "bg-green-100 text-green-700"
                      : session.status === "paused"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {session.status}
                </span>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(session.id);
              }}
              className="p-2 hover:bg-red-50 rounded-lg transition-colors text-gray-400 hover:text-red-500"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

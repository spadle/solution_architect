import { ArrowLeft, Download, Eye } from "lucide-react";
import { useDiagramStore } from "../../stores/diagramStore";
import { useSessionStore } from "../../stores/sessionStore";

interface HeaderProps {
  onBack: () => void;
  onExport: (format: string) => void;
}

export function Header({ onBack, onExport }: HeaderProps) {
  const session = useSessionStore((s) => s.session);
  const wsConnected = useSessionStore((s) => s.wsConnected);
  const renderer = useDiagramStore((s) => s.renderer);
  const setRenderer = useDiagramStore((s) => s.setRenderer);

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-4">
      <button
        onClick={onBack}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
      </button>

      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-gray-900 truncate">
          {session?.title || "Solution Architect"}
        </h1>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="capitalize">
            {session?.mode_id?.replace(/_/g, " ")}
          </span>
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              wsConnected ? "bg-green-500" : "bg-red-400"
            }`}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Renderer toggle */}
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setRenderer("reactflow")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              renderer === "reactflow"
                ? "bg-white shadow-sm text-gray-900"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            React Flow
          </button>
          <button
            onClick={() => setRenderer("mermaid")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              renderer === "mermaid"
                ? "bg-white shadow-sm text-gray-900"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Mermaid
          </button>
        </div>

        {/* Export */}
        <button
          onClick={() => onExport("json")}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Export diagram"
        >
          <Download className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}

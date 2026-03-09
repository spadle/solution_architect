import { Download, FileJson, FileCode } from "lucide-react";
import { exportDiagram, getMermaid } from "../../api/sessions";
import { useSessionStore } from "../../stores/sessionStore";

export function ExportControls() {
  const session = useSessionStore((s) => s.session);

  const handleExport = async (format: string) => {
    if (!session) return;

    try {
      if (format === "json") {
        const data = await exportDiagram(session.id, "json");
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: "application/json",
        });
        downloadBlob(blob, `${session.title}-diagram.json`);
      } else if (format === "mermaid") {
        const data = await getMermaid(session.id);
        const blob = new Blob([data.syntax], { type: "text/plain" });
        downloadBlob(blob, `${session.title}-diagram.mmd`);
      }
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  return (
    <div className="flex gap-1">
      <button
        onClick={() => handleExport("json")}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        title="Export as JSON"
      >
        <FileJson className="w-4 h-4" />
      </button>
      <button
        onClick={() => handleExport("mermaid")}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        title="Export as Mermaid"
      >
        <FileCode className="w-4 h-4" />
      </button>
    </div>
  );
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

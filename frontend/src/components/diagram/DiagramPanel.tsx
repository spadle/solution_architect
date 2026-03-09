import { useDiagramStore } from "../../stores/diagramStore";
import { MermaidViewer } from "./MermaidViewer";
import { ReactFlowViewer } from "./ReactFlowViewer";

export function DiagramPanel() {
  const renderer = useDiagramStore((s) => s.renderer);

  return (
    <div className="h-full bg-white">
      {renderer === "mermaid" ? <MermaidViewer /> : <ReactFlowViewer />}
    </div>
  );
}

import { useEffect, useRef, useCallback } from "react";
import mermaid from "mermaid";
import { useDiagramStore } from "../../stores/diagramStore";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  flowchart: {
    curve: "basis",
    padding: 15,
    nodeSpacing: 50,
    rankSpacing: 60,
    useMaxWidth: true,
  },
  securityLevel: "loose",
});

export function MermaidViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mermaidSyntax = useDiagramStore((s) => s.mermaidSyntax);
  const nodes = useDiagramStore((s) => s.nodes);

  const renderDiagram = useCallback(async () => {
    if (!containerRef.current || !mermaidSyntax) return;

    try {
      const id = `mermaid-${Date.now()}`;
      const { svg } = await mermaid.render(id, mermaidSyntax);
      containerRef.current.innerHTML = svg;
    } catch (err) {
      console.error("Mermaid render error:", err);
      if (containerRef.current) {
        containerRef.current.innerHTML = `
          <div class="text-sm text-gray-500 p-4">
            <p>Diagram preview unavailable</p>
            <pre class="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto">${mermaidSyntax}</pre>
          </div>
        `;
      }
    }
  }, [mermaidSyntax]);

  useEffect(() => {
    renderDiagram();
  }, [renderDiagram]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        Diagram will appear here as the conversation progresses...
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-4">
      <div ref={containerRef} className="flex justify-center" />
    </div>
  );
}

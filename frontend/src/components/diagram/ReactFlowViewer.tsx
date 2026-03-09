import { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useDiagramStore } from "../../stores/diagramStore";
import { nodeTypes } from "./NodeTypes";

export function ReactFlowViewer() {
  const diagramNodes = useDiagramStore((s) => s.nodes);
  const diagramEdges = useDiagramStore((s) => s.edges);

  const initialNodes: Node[] = useMemo(
    () =>
      diagramNodes.map((n) => ({
        id: n.id,
        type: "custom",
        position: { x: n.position_x || 0, y: n.position_y || 0 },
        data: {
          label: n.label,
          nodeType: n.node_type,
          status: n.status,
          description: n.description,
          metadata: n.metadata,
        },
      })),
    [diagramNodes]
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      diagramEdges.map((e) => ({
        id: e.id,
        source: e.source_node_id,
        target: e.target_node_id,
        label: e.label || undefined,
        type: "smoothstep",
        animated: e.edge_type === "research",
        style: {
          stroke: e.is_taken ? "#6366f1" : "#d1d5db",
          strokeWidth: e.is_taken ? 2 : 1,
          strokeDasharray: e.is_taken ? undefined : "5,5",
        },
        labelStyle: { fill: "#6b7280", fontSize: 11 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: e.is_taken ? "#6366f1" : "#d1d5db",
        },
      })),
    [diagramEdges]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes/edges when diagram store changes
  useMemo(() => {
    // This triggers re-render with new initial values
  }, [initialNodes, initialEdges]);

  if (diagramNodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        Diagram will appear here as the conversation progresses...
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={initialNodes}
        edges={initialEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color="#e5e7eb" />
        <Controls position="bottom-right" />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as { nodeType?: string };
            switch (data?.nodeType) {
              case "question":
                return "#818cf8";
              case "answer":
                return "#34d399";
              case "start":
                return "#a78bfa";
              case "summary":
                return "#fbbf24";
              default:
                return "#9ca3af";
            }
          }}
          position="bottom-left"
        />
      </ReactFlow>
    </div>
  );
}

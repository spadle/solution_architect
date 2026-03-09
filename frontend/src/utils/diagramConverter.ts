import type { DiagramNode, DiagramEdge } from "../types/diagram";
import type { Node, Edge } from "@xyflow/react";
import { MarkerType } from "@xyflow/react";

export function toReactFlowNodes(nodes: DiagramNode[]): Node[] {
  return nodes.map((n) => ({
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
  }));
}

export function toReactFlowEdges(edges: DiagramEdge[]): Edge[] {
  return edges.map((e) => ({
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
  }));
}

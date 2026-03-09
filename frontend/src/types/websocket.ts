import type { DiagramNode, DiagramEdge } from "./diagram";

export interface DiagramEvent {
  type:
    | "node_added"
    | "node_updated"
    | "edge_added"
    | "edge_updated"
    | "section_complete"
    | "full_sync"
    | "error";
  node?: DiagramNode;
  edge?: DiagramEdge;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

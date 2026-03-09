export interface DiagramNode {
  id: string;
  session_id: string;
  node_type:
    | "question"
    | "decision"
    | "answer"
    | "info"
    | "start"
    | "end"
    | "research"
    | "summary";
  label: string;
  description: string | null;
  status: "pending" | "active" | "answered" | "skipped";
  metadata: Record<string, unknown> | null;
  position_x: number | null;
  position_y: number | null;
  created_at: string;
}

export interface DiagramEdge {
  id: string;
  session_id: string;
  source_node_id: string;
  target_node_id: string;
  label: string | null;
  edge_type: "flow" | "decision" | "skip" | "research";
  is_taken: boolean;
  created_at: string;
}

export interface DiagramState {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
}

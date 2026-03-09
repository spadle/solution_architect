import { create } from "zustand";
import type { DiagramNode, DiagramEdge } from "../types/diagram";
import type { DiagramEvent } from "../types/websocket";

type RendererType = "mermaid" | "reactflow";

interface DiagramStore {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  renderer: RendererType;
  mermaidSyntax: string;

  addNode: (node: DiagramNode) => void;
  updateNode: (id: string, updates: Partial<DiagramNode>) => void;
  addEdge: (edge: DiagramEdge) => void;
  updateEdge: (id: string, updates: Partial<DiagramEdge>) => void;
  setFullState: (nodes: DiagramNode[], edges: DiagramEdge[]) => void;
  setRenderer: (renderer: RendererType) => void;
  setMermaidSyntax: (syntax: string) => void;
  handleEvent: (event: DiagramEvent) => void;
  clear: () => void;
}

export const useDiagramStore = create<DiagramStore>((set) => ({
  nodes: [],
  edges: [],
  renderer: "reactflow",
  mermaidSyntax: "",

  addNode: (node) =>
    set((state) => ({
      nodes: [...state.nodes, node],
    })),

  updateNode: (id, updates) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, ...updates } : n)),
    })),

  addEdge: (edge) =>
    set((state) => ({
      edges: [...state.edges, edge],
    })),

  updateEdge: (id, updates) =>
    set((state) => ({
      edges: state.edges.map((e) => (e.id === id ? { ...e, ...updates } : e)),
    })),

  setFullState: (nodes, edges) => set({ nodes, edges }),

  setRenderer: (renderer) => set({ renderer }),

  setMermaidSyntax: (syntax) => set({ mermaidSyntax: syntax }),

  handleEvent: (event) =>
    set((state) => {
      switch (event.type) {
        case "node_added":
          if (event.node) {
            return { nodes: [...state.nodes, event.node] };
          }
          return state;
        case "node_updated":
          if (event.node) {
            return {
              nodes: state.nodes.map((n) =>
                n.id === event.node!.id ? event.node! : n
              ),
            };
          }
          return state;
        case "edge_added":
          if (event.edge) {
            return { edges: [...state.edges, event.edge] };
          }
          return state;
        case "edge_updated":
          if (event.edge) {
            return {
              edges: state.edges.map((e) =>
                e.id === event.edge!.id ? event.edge! : e
              ),
            };
          }
          return state;
        case "full_sync":
          if (event.metadata) {
            return {
              nodes: (event.metadata.nodes as DiagramNode[]) || [],
              edges: (event.metadata.edges as DiagramEdge[]) || [],
            };
          }
          return state;
        default:
          return state;
      }
    }),

  clear: () => set({ nodes: [], edges: [], mermaidSyntax: "" }),
}));

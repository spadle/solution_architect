export interface Session {
  id: string;
  title: string;
  mode_id: string;
  status: "active" | "paused" | "completed";
  current_node_id: string | null;
  context_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface Mode {
  id: string;
  name: string;
  description: string;
  icon: string;
  question_categories: string[];
  initial_question: string;
}

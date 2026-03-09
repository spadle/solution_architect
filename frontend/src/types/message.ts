export interface Message {
  id: string;
  session_id: string;
  sequence: number;
  role: "user" | "assistant" | "system";
  content: string;
  structured_data: QuestionData | null;
  node_id: string | null;
  created_at: string;
}

export interface QuestionData {
  question_text: string;
  question_type:
    | "single_choice"
    | "multiple_choice"
    | "free_text"
    | "yes_no"
    | "scale";
  choices: string[];
  category: string;
  reasoning: string;
}

export interface ConversationResponse {
  message: Message;
  question: QuestionData | null;
  diagram_updates: number;
}

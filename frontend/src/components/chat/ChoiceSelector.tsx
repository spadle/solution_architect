import type { QuestionData } from "../../types/message";

interface ChoiceSelectorProps {
  question: QuestionData;
  onSelect: (choice: string) => void;
  disabled: boolean;
}

export function ChoiceSelector({
  question,
  onSelect,
  disabled,
}: ChoiceSelectorProps) {
  if (question.question_type === "free_text") {
    return null; // Handled by the text input
  }

  if (question.choices.length === 0) {
    return null;
  }

  return (
    <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
      <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">
        Quick answers
      </p>
      <div className="flex flex-wrap gap-2">
        {question.choices.map((choice, i) => (
          <button
            key={i}
            onClick={() => onSelect(choice)}
            disabled={disabled}
            className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg
                       hover:border-primary-400 hover:bg-primary-50 hover:text-primary-700
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {choice}
          </button>
        ))}
      </div>
    </div>
  );
}

import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  HelpCircle,
  CheckCircle,
  Info,
  Search,
  FileText,
  Play,
} from "lucide-react";

interface CustomNodeData {
  label: string;
  nodeType: string;
  status: string;
  description?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

const nodeStyles: Record<string, { bg: string; border: string; icon: typeof Info }> = {
  question: { bg: "bg-indigo-50", border: "border-indigo-300", icon: HelpCircle },
  answer: { bg: "bg-emerald-50", border: "border-emerald-300", icon: CheckCircle },
  decision: { bg: "bg-indigo-50", border: "border-indigo-300", icon: HelpCircle },
  info: { bg: "bg-cyan-50", border: "border-cyan-300", icon: Info },
  start: { bg: "bg-violet-50", border: "border-violet-300", icon: Play },
  summary: { bg: "bg-amber-50", border: "border-amber-300", icon: FileText },
  research: { bg: "bg-pink-50", border: "border-pink-300", icon: Search },
};

export function CustomNode({ data }: NodeProps) {
  const nodeData = data as CustomNodeData;
  const style = nodeStyles[nodeData.nodeType] || nodeStyles.info;
  const Icon = style.icon;
  const isSkipped = nodeData.status === "skipped";

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <div
        className={`px-4 py-3 rounded-xl border-2 shadow-sm min-w-[180px] max-w-[280px]
          ${style.bg} ${style.border}
          ${isSkipped ? "opacity-40" : ""}
          ${nodeData.status === "active" ? "ring-2 ring-indigo-400 ring-offset-2" : ""}
        `}
      >
        <div className="flex items-start gap-2">
          <Icon
            className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
              isSkipped ? "text-gray-400" : "text-gray-600"
            }`}
          />
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-800 leading-snug">
              {nodeData.label}
            </p>
            {nodeData.description && (
              <p className="text-xs text-gray-500 mt-1 leading-snug">
                {nodeData.description}
              </p>
            )}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </>
  );
}

export const nodeTypes = {
  custom: CustomNode,
};

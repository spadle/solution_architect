import {
  Building2,
  Plug,
  Database,
  Cloud,
  Shield,
  type LucideIcon,
} from "lucide-react";
import type { Mode } from "../../types/session";

const iconMap: Record<string, LucideIcon> = {
  building: Building2,
  plug: Plug,
  database: Database,
  cloud: Cloud,
  shield: Shield,
};

interface ModeSelectorProps {
  modes: Mode[];
  onSelect: (mode: Mode) => void;
  loading: boolean;
}

export function ModeSelector({ modes, onSelect, loading }: ModeSelectorProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            Solution Architect
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Interactive consultation tool that builds visual workflow diagrams
            as you define your solution requirements.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {modes.map((mode) => {
            const Icon = iconMap[mode.icon] || Building2;
            return (
              <button
                key={mode.id}
                onClick={() => onSelect(mode)}
                disabled={loading}
                className="card text-left hover:border-primary-300 hover:shadow-md
                           transition-all group disabled:opacity-50"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-primary-50 rounded-lg group-hover:bg-primary-100 transition-colors">
                    <Icon className="w-5 h-5 text-primary-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">{mode.name}</h3>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {mode.description}
                </p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {mode.question_categories.slice(0, 3).map((cat) => (
                    <span
                      key={cat}
                      className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full"
                    >
                      {cat.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

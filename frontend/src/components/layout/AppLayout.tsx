import { ReactNode, useState, useCallback } from "react";

interface AppLayoutProps {
  chat: ReactNode;
  diagram: ReactNode;
  header: ReactNode;
}

export function AppLayout({ chat, diagram, header }: AppLayoutProps) {
  const [splitPercent, setSplitPercent] = useState(40);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = useCallback(() => {
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      const container = e.currentTarget as HTMLElement;
      const rect = container.getBoundingClientRect();
      const percent = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPercent(Math.min(Math.max(percent, 25), 75));
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <div className="h-screen flex flex-col">
      {header}
      <div
        className="flex-1 flex overflow-hidden"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Chat panel */}
        <div
          className="flex flex-col overflow-hidden"
          style={{ width: `${splitPercent}%` }}
        >
          {chat}
        </div>

        {/* Divider */}
        <div
          className={`w-1 cursor-col-resize hover:bg-primary-400 transition-colors ${
            isDragging ? "bg-primary-500" : "bg-gray-200"
          }`}
          onMouseDown={handleMouseDown}
        />

        {/* Diagram panel */}
        <div
          className="flex flex-col overflow-hidden"
          style={{ width: `${100 - splitPercent}%` }}
        >
          {diagram}
        </div>
      </div>
    </div>
  );
}

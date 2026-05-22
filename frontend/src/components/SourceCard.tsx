"use client";
import type { SourceDoc } from "@/lib/api";
import { FileText, MessageSquare, Globe } from "lucide-react";

const ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-3.5 h-3.5" />,
  confluence: <Globe className="w-3.5 h-3.5" />,
  slack: <MessageSquare className="w-3.5 h-3.5" />,
};

export function SourceCard({ source, index }: { source: SourceDoc; index: number }) {
  const icon = ICONS[source.source_type] ?? <FileText className="w-3.5 h-3.5" />;
  const title = source.title ?? source.source_id;

  return (
    <div className="flex gap-2 p-2.5 bg-zinc-800/50 rounded-lg border border-zinc-700/50 text-xs group">
      <span className="text-zinc-500 font-mono mt-0.5">[{index}]</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 text-zinc-300 font-medium truncate">
          <span className="text-zinc-500">{icon}</span>
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-400 truncate transition-colors"
            >
              {title}
            </a>
          ) : (
            <span className="truncate">{title}</span>
          )}
          <span className="ml-auto text-zinc-600 shrink-0">{(source.score * 100).toFixed(0)}%</span>
        </div>
        <p className="text-zinc-500 mt-1 line-clamp-2 leading-relaxed">{source.content_excerpt}</p>
      </div>
    </div>
  );
}

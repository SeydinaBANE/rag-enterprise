"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { SourceCard } from "./SourceCard";
import type { SourceDoc } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDoc[];
  isStreaming?: boolean;
  queryLogId?: string;
  feedback?: 1 | -1 | null;
}

interface MessageBubbleProps {
  message: Message;
  onFeedback?: (messageId: string, feedback: 1 | -1) => void;
}

export function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] px-4 py-2.5 bg-blue-600 text-white rounded-2xl rounded-br-md text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  const voted = message.feedback !== undefined && message.feedback !== null;

  return (
    <div className="flex flex-col gap-3 max-w-[90%]">
      <div className="px-4 py-3 bg-zinc-800 rounded-2xl rounded-bl-md text-sm text-zinc-100 leading-relaxed prose prose-invert prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        {message.isStreaming && (
          <span className="inline-block w-1.5 h-4 bg-zinc-400 animate-pulse ml-0.5 align-middle" />
        )}
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="flex flex-col gap-1.5 px-1">
          <span className="text-xs text-zinc-500 font-medium">Sources</span>
          {message.sources.map((src, i) => (
            <SourceCard key={src.id} source={src} index={i + 1} />
          ))}
        </div>
      )}

      {!message.isStreaming && message.queryLogId && (
        <div className="flex items-center gap-1 px-1">
          <span className="text-xs text-zinc-600">Utile ?</span>
          <button
            onClick={() => !voted && onFeedback?.(message.id, 1)}
            disabled={voted}
            title="Réponse utile"
            className={cn(
              "p-1 rounded transition-colors",
              message.feedback === 1
                ? "text-green-400"
                : "text-zinc-600 hover:text-green-400 hover:bg-zinc-700 disabled:cursor-default"
            )}
          >
            <ThumbsUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => !voted && onFeedback?.(message.id, -1)}
            disabled={voted}
            title="Réponse inexacte"
            className={cn(
              "p-1 rounded transition-colors",
              message.feedback === -1
                ? "text-red-400"
                : "text-zinc-600 hover:text-red-400 hover:bg-zinc-700 disabled:cursor-default"
            )}
          >
            <ThumbsDown className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

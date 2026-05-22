"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SourceCard } from "./SourceCard";
import type { SourceDoc } from "@/lib/api";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDoc[];
  isStreaming?: boolean;
}

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] px-4 py-2.5 bg-blue-600 text-white rounded-2xl rounded-br-md text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

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
    </div>
  );
}

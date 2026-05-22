"use client";
import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { EmptyState } from "./EmptyState";
import { streamQuery, submitFeedback } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";

const COLLECTION_LABELS: Record<string, string> = {
  general: "Général",
  rh: "RH",
  tech: "Tech",
  finance: "Finance",
};

export function Chat() {
  const messages = useStore((s) => s.messages);
  const addMessage = useStore((s) => s.addMessage);
  const updateMessage = useStore((s) => s.updateMessage);
  const appendToken = useStore((s) => s.appendToken);
  const collection = useStore((s) => s.collection);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setLoading(true);

    const assistantId = crypto.randomUUID();
    addMessage({ id: crypto.randomUUID(), role: "user", content: question });
    addMessage({ id: assistantId, role: "assistant", content: "", isStreaming: true });

    try {
      for await (const chunk of streamQuery(question, collection)) {
        if (chunk.type === "token" && chunk.content) {
          appendToken(assistantId, chunk.content);
        } else if (chunk.type === "sources" && chunk.sources) {
          updateMessage(assistantId, { sources: chunk.sources });
        } else if (chunk.type === "done") {
          updateMessage(assistantId, {
            isStreaming: false,
            queryLogId: chunk.query_log_id,
          });
        } else if (chunk.type === "error") {
          updateMessage(assistantId, {
            content: chunk.content ?? "Une erreur est survenue.",
            isStreaming: false,
          });
        }
      }
    } catch {
      updateMessage(assistantId, {
        content: "Erreur de connexion à l'API.",
        isStreaming: false,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(messageId: string, feedback: 1 | -1) {
    const msg = messages.find((m) => m.id === messageId);
    if (!msg?.queryLogId || (msg.feedback !== undefined && msg.feedback !== null)) return;
    updateMessage(messageId, { feedback });
    try {
      await submitFeedback(msg.queryLogId, feedback);
    } catch {
      // fire-and-forget — feedback failure is non-critical
    }
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-900 text-zinc-100">
      <header className="flex items-center px-6 py-4 border-b border-zinc-800">
        <div>
          <h1 className="text-lg font-semibold">Base de connaissances</h1>
          <p className="text-xs text-zinc-500">
            Collection :{" "}
            <span className="text-zinc-300">{COLLECTION_LABELS[collection] ?? collection}</span>
          </p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState onSuggest={setInput} />
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onFeedback={msg.role === "assistant" ? handleFeedback : undefined}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 px-4 py-4 border-t border-zinc-800"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e as unknown as React.FormEvent);
            }
          }}
          placeholder="Posez votre question… (Entrée pour envoyer)"
          rows={1}
          className="flex-1 resize-none bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500 max-h-32 overflow-y-auto"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className={cn(
            "p-2.5 rounded-xl transition-colors",
            loading || !input.trim()
              ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-500"
          )}
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
        </button>
      </form>
    </div>
  );
}

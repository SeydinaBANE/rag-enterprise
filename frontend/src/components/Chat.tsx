"use client";
import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, Loader2 } from "lucide-react";
import { MessageBubble, type Message } from "./MessageBubble";
import { streamQuery, ingestPDF, type SourceDoc } from "@/lib/api";
import { cn } from "@/lib/utils";

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [collection, setCollection] = useState("general");
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setLoading(true);

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: question };
    const assistantId = crypto.randomUUID();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      for await (const chunk of streamQuery(question, collection)) {
        if (chunk.type === "token" && chunk.content) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + chunk.content } : m
            )
          );
        } else if (chunk.type === "sources" && chunk.sources) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, sources: chunk.sources } : m
            )
          );
        } else if (chunk.type === "done") {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m))
          );
        } else if (chunk.type === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: chunk.content ?? "Une erreur est survenue.", isStreaming: false }
                : m
            )
          );
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "Erreur de connexion à l'API.", isStreaming: false }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await ingestPDF(file, collection);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `✓ ${result.message}`,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: "Erreur lors de l'upload du PDF." },
      ]);
    }
    e.target.value = "";
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-900 text-zinc-100">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
        <div>
          <h1 className="text-lg font-semibold">Base de connaissances</h1>
          <p className="text-xs text-zinc-500">Posez une question sur vos documents internes</p>
        </div>
        <select
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          className="text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-zinc-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="general">Général</option>
          <option value="rh">RH</option>
          <option value="tech">Tech</option>
          <option value="finance">Finance</option>
        </select>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <div className="w-12 h-12 bg-blue-600/20 rounded-2xl flex items-center justify-center text-2xl">
              🔍
            </div>
            <p className="text-zinc-400 text-sm max-w-xs">
              Posez n&apos;importe quelle question sur vos documents internes. Je citerai mes sources.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 px-4 py-4 border-t border-zinc-800"
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileUpload}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="p-2.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-xl transition-colors"
          title="Uploader un PDF"
        >
          <Paperclip className="w-5 h-5" />
        </button>
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

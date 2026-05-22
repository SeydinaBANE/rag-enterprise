"use client";

import { Brain } from "lucide-react";

const SUGGESTIONS = [
  "Quelle est la politique de congés ?",
  "Comment soumettre une note de frais ?",
  "Quelles sont les procédures d'onboarding technique ?",
  "Quel est le processus de validation budgétaire ?",
];

interface EmptyStateProps {
  onSuggest: (question: string) => void;
}

export function EmptyState({ onSuggest }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4 text-center">
      <Brain className="w-12 h-12 text-blue-500/60" />
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-zinc-200">Base de connaissances</h2>
        <p className="text-sm text-zinc-500 max-w-sm">
          Posez une question sur vos documents internes ou choisissez une suggestion ci-dessous.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2 max-w-lg">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => onSuggest(q)}
            className="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 hover:border-zinc-600 text-zinc-300 text-xs rounded-full px-3 py-1.5 transition-colors text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

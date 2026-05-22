"use client";
import { useState } from "react";
import { login, logout } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { LogIn, LogOut, X } from "lucide-react";

export function LoginButton() {
  const { user, setUser } = useStore();
  const [open, setOpen] = useState(false);

  if (user) {
    return (
      <div className="flex items-center gap-2 text-sm text-zinc-400">
        <span className="truncate max-w-[120px]" title={user.email}>{user.email}</span>
        {user.role === "admin" && (
          <span className="px-1.5 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400">admin</span>
        )}
        <button
          onClick={async () => { await logout(); setUser(null); }}
          className="p-1 rounded hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300"
          title="Déconnexion"
        >
          <LogOut size={14} />
        </button>
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm bg-blue-600 hover:bg-blue-500 text-white transition-colors"
      >
        <LogIn size={14} />
        Connexion
      </button>
      {open && <LoginModal onClose={() => setOpen(false)} />}
    </>
  );
}

function LoginModal({ onClose }: { onClose: () => void }) {
  const setUser = useStore((s) => s.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
      setUser(user);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-sm bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300"
        >
          <X size={16} />
        </button>
        <h2 className="text-lg font-semibold text-white mb-5">Connexion</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-white text-sm placeholder-zinc-500 focus:outline-none focus:border-blue-500"
              placeholder="vous@exemple.com"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-white text-sm placeholder-zinc-500 focus:outline-none focus:border-blue-500"
              placeholder="••••••••"
            />
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            {loading ? "Connexion…" : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}

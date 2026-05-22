"use client";

import { FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { UploadZone } from "./UploadZone";
import { useStore, type IngestionJob } from "@/store/useStore";
import { ingestPDF } from "@/lib/api";

const COLLECTIONS = [
  { value: "general", label: "Général" },
  { value: "rh", label: "RH" },
  { value: "tech", label: "Tech" },
  { value: "finance", label: "Finance" },
];

export function DocumentPanel() {
  const collection = useStore((s) => s.collection);
  const setCollection = useStore((s) => s.setCollection);
  const ingestionJobs = useStore((s) => s.ingestionJobs);
  const addIngestionJob = useStore((s) => s.addIngestionJob);
  const updateIngestionJob = useStore((s) => s.updateIngestionJob);

  async function handleUpload(file: File) {
    const tempId = crypto.randomUUID();
    addIngestionJob({ id: tempId, filename: file.name, collection, status: "uploading" });
    try {
      const result = await ingestPDF(file, collection);
      updateIngestionJob(tempId, { id: result.job_id, status: "done" });
    } catch {
      updateIngestionJob(tempId, { status: "error", error: "Échec de l'envoi" });
    }
  }

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col h-screen bg-zinc-900 border-r border-zinc-800">
      <div className="px-4 py-4 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-200">Documents</h2>
        <p className="text-xs text-zinc-500 mt-0.5">Gérer vos sources de données</p>
      </div>

      <div className="px-4 py-3 border-b border-zinc-800 space-y-1.5">
        <label className="text-xs text-zinc-500 uppercase tracking-wide font-medium">
          Collection
        </label>
        <select
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {COLLECTIONS.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div className="px-4 py-3 border-b border-zinc-800">
        <label className="text-xs text-zinc-500 uppercase tracking-wide font-medium block mb-2">
          Importer un PDF
        </label>
        <UploadZone onUpload={handleUpload} />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium mb-2">
          Documents importés
        </p>
        {ingestionJobs.length === 0 ? (
          <p className="text-xs text-zinc-600 text-center mt-6">Aucun document chargé</p>
        ) : (
          <ul className="space-y-2">
            {ingestionJobs.map((job) => (
              <IngestionJobRow key={job.id} job={job} />
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

function IngestionJobRow({ job }: { job: IngestionJob }) {
  return (
    <li className="flex items-start gap-2 p-2 rounded-lg bg-zinc-800/50 border border-zinc-800">
      <FileText className="w-4 h-4 text-zinc-500 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-zinc-300 truncate" title={job.filename}>
          {job.filename}
        </p>
        <StatusBadge job={job} />
      </div>
    </li>
  );
}

function StatusBadge({ job }: { job: IngestionJob }) {
  if (job.status === "uploading") {
    return (
      <span className="flex items-center gap-1 text-xs text-zinc-400 mt-0.5">
        <Loader2 className="w-3 h-3 animate-spin" /> Envoi…
      </span>
    );
  }
  if (job.status === "pending") {
    return (
      <span className="flex items-center gap-1 text-xs text-yellow-400 mt-0.5">
        <Loader2 className="w-3 h-3 animate-spin" /> Traitement…
      </span>
    );
  }
  if (job.status === "done") {
    return (
      <span className="flex items-center gap-1 text-xs text-green-400 mt-0.5">
        <CheckCircle2 className="w-3 h-3" /> Ajouté ✓
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs text-red-400 mt-0.5">
      <AlertCircle className="w-3 h-3" /> {job.error ?? "Erreur"}
    </span>
  );
}

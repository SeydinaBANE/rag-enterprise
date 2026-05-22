"use client";

import { useRef, useState, useEffect } from "react";
import { UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

export function UploadZone({ onUpload, disabled }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 3000);
    return () => clearTimeout(t);
  }, [error]);

  function validateAndUpload(file: File | null | undefined) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
      setError("Seuls les fichiers PDF sont acceptés");
      return;
    }
    onUpload(file);
  }

  return (
    <div
      className={cn(
        "relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer select-none transition-colors",
        isDragging
          ? "border-blue-500 bg-blue-500/10"
          : "border-zinc-700 bg-zinc-800/50 hover:border-zinc-600",
        disabled && "opacity-50 cursor-not-allowed pointer-events-none"
      )}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        validateAndUpload(e.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(e) => validateAndUpload(e.target.files?.[0])}
        onClick={(e) => { (e.target as HTMLInputElement).value = ""; }}
      />
      <UploadCloud className="mx-auto mb-2 w-6 h-6 text-zinc-500" />
      {error ? (
        <p className="text-xs text-red-400">{error}</p>
      ) : (
        <>
          <p className="text-xs text-zinc-400 font-medium">Déposer un PDF ici</p>
          <p className="text-xs text-zinc-600 mt-0.5">ou cliquer pour parcourir</p>
        </>
      )}
    </div>
  );
}

import { DocumentPanel } from "@/components/DocumentPanel";
import { Chat } from "@/components/Chat";

export default function HomePage() {
  return (
    <div className="flex h-screen overflow-hidden bg-zinc-900">
      <DocumentPanel />
      <main className="flex-1 min-w-0">
        <Chat />
      </main>
    </div>
  );
}

import { STATUS_LABELS } from "@/lib/format";

const toneByStatus: Record<string, string> = {
  published: "chip-live",
  pending_moderation: "chip-accent",
  draft: "",
  paused: "chip-accent",
  expired: "chip-danger",
  rejected: "chip-danger",
  sold: "chip-brand",
  archived: "",
};

export function StatusChip({ status }: { status: string }) {
  return (
    <span className={`chip ${toneByStatus[status] ?? ""}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

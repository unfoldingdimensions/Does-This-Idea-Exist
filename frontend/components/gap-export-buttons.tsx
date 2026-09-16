"use client";

import * as React from "react";
import { FileJson, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CompareNotConfirmed, exportGapTable, type ExportFormat } from "@/lib/api";

/**
 * The gap table's three exports (§5) — Markdown / JSON / CSV. `/api/export/{format}`
 * is stateless and never triggers a capture, so these are safe the moment the
 * table renders. The bytes are downloaded straight from the response; the one
 * refusal that is a state rather than a fault (an unconfirmed draft) says so.
 */

interface FormatSpec {
  format: ExportFormat;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const FORMATS: readonly FormatSpec[] = [
  { format: "markdown", label: "Markdown", icon: FileText },
  { format: "json", label: "JSON", icon: FileJson },
  { format: "csv", label: "CSV", icon: FileSpreadsheet },
] as const;

/** Save the returned text as a file. The object URL is revoked once the click
 * has been handed to the browser, so nothing leaks. */
function saveFile(text: string, mediaType: string, filename: string) {
  const blob = new Blob([text], { type: mediaType || "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Defer the revoke a beat: Safari/Firefox can drop a download whose object URL
  // is revoked in the same tick as the click.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function GapExportButtons({
  you,
  competitors,
  disabled = false,
}: {
  you: string;
  competitors: string[];
  disabled?: boolean;
}) {
  const [busy, setBusy] = React.useState<ExportFormat | null>(null);

  const run = async (spec: FormatSpec) => {
    if (busy !== null || disabled) return;
    setBusy(spec.format);
    try {
      const payload = await exportGapTable(spec.format, you, competitors);
      saveFile(payload.text, payload.mediaType, payload.filename);
      toast.success(`${spec.label} exported`, { description: payload.filename });
    } catch (err) {
      const message =
        err instanceof CompareNotConfirmed
          ? `Confirm your draft first — ${err.message}`
          : err instanceof Error
            ? err.message
            : "The export could not be generated.";
      toast.error(`Couldn't export ${spec.label}`, { description: message });
    } finally {
      setBusy(null);
    }
  };

  const blocked = disabled || busy !== null || you.trim().length === 0;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {FORMATS.map((spec) => {
        const Icon = spec.icon;
        const thisBusy = busy === spec.format;
        return (
          <Button
            key={spec.format}
            type="button"
            variant="outline"
            size="sm"
            disabled={blocked}
            aria-busy={thisBusy}
            onClick={() => void run(spec)}
          >
            {thisBusy ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
                Exporting…
              </>
            ) : (
              <>
                <Icon className="h-3.5 w-3.5" />
                {spec.label}
              </>
            )}
          </Button>
        );
      })}
    </div>
  );
}

import { useState } from "react";
import { Loader2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AnalyzeResponse,
  appendModificationHistory,
  loadModificationHistory,
  modifyArchitecture,
  saveLastResult,
} from "@/lib/api";
import { toast } from "sonner";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { getUserFacingApiMessage, isApiKeyError, notifyApiError } from "@/lib/apiErrors";
import { recordApiKeyErrorType } from "@/components/ApiKeyStatusBadge";

type Props = {
  result: AnalyzeResponse;
  onUpdated: (next: AnalyzeResponse) => void;
};

export function ModifyArchitecturePanel({ result, onUpdated }: Props) {
  const [request, setRequest] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiKeyAlert, setApiKeyAlert] = useState<string | null>(null);
  const [lastChange, setLastChange] = useState<string[]>([]);
  const history = loadModificationHistory();

  const handleUpdate = async () => {
    if (!request.trim()) {
      toast.error("Describe what you want to change");
      return;
    }
    setLoading(true);
    try {
      const res = await modifyArchitecture({
        mode: result.mode,
        current_architecture: result,
        user_change_request: request.trim(),
      });
      const updated = res.updated_architecture as AnalyzeResponse;
      saveLastResult(updated);
      onUpdated(updated);
      setLastChange(res.changes_applied || []);
      appendModificationHistory({
        request: request.trim(),
        response: res,
        at: new Date().toISOString(),
      });
      toast.success("Architecture updated");
      setRequest("");
    } catch (e) {
      if (isApiKeyError(e)) {
        setApiKeyAlert(getUserFacingApiMessage(e));
        const t = e.apiError!.error_type;
        if (t === "API_KEY_INVALID" || t === "API_KEY_MISSING") {
          recordApiKeyErrorType(t);
        }
      }
      notifyApiError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="glass-card p-6 mt-8">
      <div className="flex items-center gap-3 mb-4">
        <Pencil className="h-5 w-5 text-primary" />
        <h2 className="text-xl font-semibold">Modify Architecture</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        Describe changes in plain language (e.g. switch database to PostgreSQL, add JWT auth, simplify for a mini project).
      </p>
      {apiKeyAlert ? (
        <ApiErrorAlert className="mb-4" message={apiKeyAlert} onDismiss={() => setApiKeyAlert(null)} />
      ) : null}
      <Label htmlFor="change-req">What do you want to change?</Label>
      <Textarea
        id="change-req"
        className="mt-2 min-h-[90px]"
        placeholder="Change database from MongoDB to PostgreSQL and add JWT authentication..."
        value={request}
        onChange={(e) => setRequest(e.target.value)}
      />
      <Button className="mt-4 gap-2" variant="hero" onClick={handleUpdate} disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Update Architecture
      </Button>

      {lastChange.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium mb-2">Changes applied</h3>
          <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
            {lastChange.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {history.length > 0 && (
        <div className="mt-6 pt-4 border-t border-border/50">
          <h3 className="text-sm font-medium mb-2">Modification history ({history.length})</h3>
          <p className="text-xs text-muted-foreground">Stored in this browser session.</p>
        </div>
      )}
    </section>
  );
}


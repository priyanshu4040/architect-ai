import { useEffect, useState } from "react";
import { fetchApiKeyStatus, validateApiKey } from "@/lib/api";
import {
  mapStatusToIndicator,
  type ApiErrorType,
  type ApiKeyConnectionStatus,
} from "@/lib/apiErrors";

const LAST_KEY_ERROR = "architect_ai:last_api_key_error";

const LABELS: Record<ApiKeyConnectionStatus, string> = {
  connected: "API: Connected",
  missing: "API: No Key",
  invalid: "API: Invalid Key",
  quota_exhausted: "API: Quota Exhausted",
  unknown: "API: Unknown",
};

const STYLES: Record<ApiKeyConnectionStatus, string> = {
  connected: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  missing: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  invalid: "bg-destructive/15 text-destructive",
  quota_exhausted: "bg-destructive/15 text-destructive",
  unknown: "bg-muted text-muted-foreground",
};

export function ApiKeyStatusBadge() {
  const [status, setStatus] = useState<ApiKeyConnectionStatus>("unknown");

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await fetchApiKeyStatus();
        if (cancelled) return;

        if (data.status === "missing") {
          setStatus("missing");
          return;
        }

        const validation = await validateApiKey();
        if (cancelled) return;

        if (validation.valid) {
          clearApiKeyErrorType();
          setStatus("connected");
          return;
        }

        const errType = validation.error_type;
        if (errType === "API_KEY_EXHAUSTED" || errType === "API_RATE_LIMIT") {
          setStatus("quota_exhausted");
        } else if (errType === "API_KEY_INVALID") {
          setStatus("invalid");
        } else {
          setStatus(mapStatusToIndicator(data, errType));
        }
      } catch {
        if (!cancelled) setStatus("unknown");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <span
      className={`hidden lg:inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
      title={LABELS[status]}
    >
      {LABELS[status]}
    </span>
  );
}

export function recordApiKeyErrorType(type: ApiErrorType) {
  sessionStorage.setItem(LAST_KEY_ERROR, type);
}

export function clearApiKeyErrorType() {
  sessionStorage.removeItem(LAST_KEY_ERROR);
}

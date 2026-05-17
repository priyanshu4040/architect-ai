import { toast } from "sonner";

export type ApiErrorType =
  | "API_KEY_EXHAUSTED"
  | "API_KEY_INVALID"
  | "API_RATE_LIMIT"
  | "API_KEY_MISSING"
  | "API_PERMISSION_DENIED"
  | "INVALID_MODEL"
  | "PROVIDER_UNREACHABLE"
  | "PROVIDER_ERROR";

export interface ApiErrorPayload {
  error: true;
  error_type: ApiErrorType;
  message: string;
}

export const API_KEY_USER_MESSAGE =
  "API token limit reached. Please change or update the API key.";

export class ApiClientError extends Error {
  readonly status: number;
  readonly apiError?: ApiErrorPayload;

  constructor(message: string, status: number, apiError?: ApiErrorPayload) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.apiError = apiError;
  }
}

export function isApiKeyError(err: unknown): err is ApiClientError {
  return err instanceof ApiClientError && !!err.apiError;
}

export function isApiKeyErrorType(type: ApiErrorType | undefined): boolean {
  return (
    type === "API_KEY_EXHAUSTED" ||
    type === "API_KEY_INVALID" ||
    type === "API_RATE_LIMIT" ||
    type === "API_KEY_MISSING"
  );
}

function parseJsonBody(text: string): Record<string, unknown> | null {
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function parseApiErrorFromBody(
  text: string,
  status: number
): ApiClientError | null {
  const json = parseJsonBody(text);
  if (!json) return null;

  if (json.error === true && typeof json.error_type === "string") {
    const payload: ApiErrorPayload = {
      error: true,
      error_type: json.error_type as ApiErrorType,
      message: String(json.message ?? API_KEY_USER_MESSAGE),
    };
    return new ApiClientError(payload.message, status, payload);
  }

  const detail = json.detail;
  if (typeof detail === "object" && detail !== null && !Array.isArray(detail)) {
    const d = detail as Record<string, unknown>;
    if (d.error === true && typeof d.error_type === "string") {
      const payload: ApiErrorPayload = {
        error: true,
        error_type: d.error_type as ApiErrorType,
        message: String(d.message ?? API_KEY_USER_MESSAGE),
      };
      return new ApiClientError(payload.message, status, payload);
    }
  }

  return null;
}

export async function throwIfApiError(res: Response): Promise<void> {
  if (res.ok) return;
  const text = await res.text();
  const parsed = parseApiErrorFromBody(text, res.status);
  if (parsed) throw parsed;
  throw new ApiClientError(text || `Request failed: ${res.status}`, res.status);
}

export function maskApiKey(key: string): string {
  const k = key.trim();
  if (!k) return "";
  if (k.length <= 10) return `${k.slice(0, 3)}****`;
  return `${k.slice(0, 6)}...${k.slice(-4)}`;
}

export function getUserFacingApiMessage(err: unknown): string {
  if (isApiKeyError(err)) {
    const type = err.apiError!.error_type;
    const msg = err.apiError!.message;
    if (type === "API_KEY_EXHAUSTED") {
      return "Your API key is valid, but quota or token limit is exhausted.";
    }
    if (type === "API_RATE_LIMIT") {
      return "Your API key is likely valid, but Groq rate limit was hit. Try again shortly.";
    }
    if (type === "API_KEY_INVALID") {
      return "Groq rejected this API key. Check GROQ_API_KEY in .env (no spaces/quotes) and restart the backend.";
    }
    if (type === "API_KEY_MISSING") {
      return "No API key configured. Add GROQ_API_KEY to your backend .env file and restart the server.";
    }
    if (type === "INVALID_MODEL") {
      return msg || "The configured Groq model name is invalid or unavailable.";
    }
    if (type === "API_PERMISSION_DENIED") {
      return msg || "API key is valid but lacks permission for this operation.";
    }
    if (type === "PROVIDER_UNREACHABLE") {
      return "Cannot reach Groq. Check network and that the backend is running.";
    }
    if (type === "PROVIDER_ERROR") {
      return msg || "Groq returned an error. See backend logs for details.";
    }
    return msg;
  }
  if (err instanceof Error && /failed to fetch|network/i.test(err.message)) {
    return "Backend is not reachable. Start the FastAPI server and check VITE_API_BASE.";
  }
  return err instanceof Error ? err.message : "Request failed";
}

export function notifyApiError(err: unknown): void {
  const message = getUserFacingApiMessage(err);
  const duration = isApiKeyError(err) ? 12_000 : 5_000;
  toast.error(message, { duration });
}

export type ApiKeyConnectionStatus =
  | "connected"
  | "missing"
  | "invalid"
  | "quota_exhausted"
  | "unknown";

export interface ApiKeyStatusResponse {
  status: string;
  error_type?: ApiErrorType;
  message?: string;
  key_count?: number;
  provider?: string;
  model?: string;
  masked_key?: string;
}

export interface ApiKeyValidateResponse {
  valid: boolean;
  error_type?: ApiErrorType;
  message: string;
  provider?: string;
  model?: string;
  masked_key?: string;
  preview?: string;
}

export function mapStatusToIndicator(
  data: ApiKeyStatusResponse | null,
  lastErrorType?: ApiErrorType
): ApiKeyConnectionStatus {
  if (lastErrorType === "API_KEY_EXHAUSTED" || lastErrorType === "API_RATE_LIMIT") {
    return "quota_exhausted";
  }
  if (lastErrorType === "API_KEY_INVALID" || lastErrorType === "API_PERMISSION_DENIED") {
    return "invalid";
  }
  if (lastErrorType === "INVALID_MODEL") return "unknown";
  if (!data) return "unknown";
  if (data.status === "missing") return "missing";
  if (data.status === "configured" && (data.key_count ?? 0) > 0) return "connected";
  return "unknown";
}
